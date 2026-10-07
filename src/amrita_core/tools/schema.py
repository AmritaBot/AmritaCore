"""Tool schema projection and argument validation.

The tool schema layer has two orthogonal axes:

* **Projection** — Python type hints and Pydantic models to
  :class:`~amrita_core.tools.models.FunctionPropertySchema` (authoring).
* **Compilation** — a :class:`~amrita_core.tools.models.FunctionParametersSchema`
  back to a Pydantic model that validates the arguments the model produced.

Both axes meet at Pydantic: the JSON Schema is the intermediate representation
the provider consumes, and a Pydantic model is the validation authority. The
projection is deliberately lossy, because no provider needs Python's full type
system, but it stays complete enough to compile back into a validator. That is
what lets a schema from any source — a type hint, a Pydantic model, or an MCP
server — be checked by the same code.
"""

from __future__ import annotations

import inspect
import math
import types
import typing
from collections.abc import Callable, Mapping, Sequence
from functools import cache, reduce
from operator import or_
from typing import (
    Annotated,
    Any,
    Literal,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    create_model,
)
from pydantic.functional_validators import AfterValidator
from pydantic_core import PydanticUndefined

from .models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
    MCPProperty,
    cast_mcp_property_to_amrita,
)

# Projection: Python type hints -> JSON Schema

_JSON_SCALAR_TYPES: dict[str, Any] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}

#: Constraint attributes Pydantic leaves on a field's metadata, keyed by the JSON Schema keyword each one feeds.
_FIELD_CONSTRAINT_KEYS: tuple[tuple[str, str], ...] = (
    ("gt", "gt"),
    ("ge", "ge"),
    ("lt", "lt"),
    ("le", "le"),
    ("min_length", "minLength"),
    ("max_length", "maxLength"),
    ("pattern", "pattern"),
    ("multiple_of", "multipleOf"),
)


def _allows_none_type(type_hint: Any) -> bool:
    """Whether a type hint is a union that includes ``None``."""
    return type(None) in get_args(type_hint)


def _field_constraints(metadata: Sequence[Any]) -> dict[str, Any]:
    """Collect the constraints Pydantic recorded for one field.

    The metadata entries come from ``annotated_types`` (``Ge``, ``MinLen``,
    ``MultipleOf``, ...) plus a few private Pydantic wrappers, so they are
    probed by attribute rather than matched by class.
    """
    found: dict[str, Any] = {}
    for entry in metadata:
        for attribute, keyword in _FIELD_CONSTRAINT_KEYS:
            value = getattr(entry, attribute, None)
            if value is not None:
                found.setdefault(keyword, value)
    return found


def _apply_field_constraints(
    schema: FunctionPropertySchema, constraints: Mapping[str, Any]
) -> None:
    """Copy Pydantic field constraints onto a projected schema, in place.

    Only the group matching the property's JSON type is applied, because the
    schema model requires string, numeric, array and object constraints to
    stay mutually exclusive.
    """
    declared = list(schema.type) if isinstance(schema.type, list) else [schema.type]
    non_null = [t for t in declared if t != "null"]

    if non_null == ["string"]:
        if (value := constraints.get("minLength")) is not None:
            schema.minLength = value
        if (value := constraints.get("maxLength")) is not None:
            schema.maxLength = value
        if (value := constraints.get("pattern")) is not None:
            schema.pattern = value
    elif len(non_null) == 1 and non_null[0] in ("integer", "number"):
        if (value := constraints.get("gt")) is not None:
            schema.exclusiveMinimum = value
        elif (value := constraints.get("ge")) is not None:
            schema.minimum = value
        if (value := constraints.get("lt")) is not None:
            schema.exclusiveMaximum = value
        elif (value := constraints.get("le")) is not None:
            schema.maximum = value
        if (value := constraints.get("multipleOf")) is not None:
            schema.multipleOf = value
    elif non_null == ["array"]:
        if (value := constraints.get("minLength")) is not None:
            schema.minItems = value
        if (value := constraints.get("maxLength")) is not None:
            schema.maxItems = value


def _is_container_type(type_hint: Any) -> bool:
    """Check if a type hint is a container type (List, Dict)"""
    if hasattr(type_hint, "__origin__"):
        origin = get_origin(type_hint)
        return origin in (list, dict)
    return False


def _is_pydantic_model(type_hint: Any) -> bool:
    """Check if a type hint is a Pydantic model"""
    try:
        return isinstance(type_hint, type) and issubclass(type_hint, BaseModel)
    except (ImportError, TypeError):
        return False


def pydantic_model_to_property_schema(
    model_class: type[BaseModel], globalns: dict[str, Any], desc: str | None = None
) -> FunctionPropertySchema:
    """Convert a Pydantic model to FunctionPropertySchema recursively"""
    if not _is_pydantic_model(model_class):
        raise ValueError(f"Expected Pydantic BaseModel, got {model_class.__name__}")

    properties: dict[str, FunctionPropertySchema] = {}
    required_fields: list[str] = []

    for field_name, field_info in model_class.__pydantic_fields__.items():
        field_type = field_info.annotation
        field_desc = field_info.description or f"Field {field_name}"

        if field_type is Any or field_type is object:
            raise ValueError(
                f"Field '{field_name}' in Pydantic model '{model_class.__name__}' "
                "uses Any or object type, which is not allowed"
            )

        field_schema = python_type_to_property_schema(field_type, globalns, field_desc)
        _apply_field_constraints(field_schema, _field_constraints(field_info.metadata))

        if field_info.is_required():
            required_fields.append(field_name)
            if _allows_none_type(field_type):
                field_schema.nullable = True
        elif field_info.default is not PydanticUndefined:
            field_schema.default = field_info.default

        properties[field_name] = field_schema

    return FunctionPropertySchema(
        type="object",
        description=(model_class.__doc__ or "").strip()
        or desc
        or f"Pydantic model {model_class.__name__}",
        properties=properties,
        required=required_fields,
    )


def python_type_to_property_schema(
    python_type: Any,
    globalns: dict[str, Any],
    description: str | None = None,
) -> FunctionPropertySchema:
    """Convert Python type to FunctionPropertySchema with full JSON Schema support"""
    has_desc = bool(description.strip() if description else False)
    description = description or "No description"
    if python_type is str:
        return FunctionPropertySchema(type="string", description=description)
    elif python_type is int:
        return FunctionPropertySchema(type="integer", description=description)
    elif python_type is float:
        return FunctionPropertySchema(type="number", description=description)
    elif python_type is bool:
        return FunctionPropertySchema(type="boolean", description=description)
    elif python_type is Any or python_type is object:
        raise ValueError(f"Type {python_type} is not allowed in tool parameters")

    if _is_pydantic_model(python_type):
        return pydantic_model_to_property_schema(
            python_type, globalns, description if has_desc else None
        )

    origin = get_origin(python_type) if python_type not in (list, dict) else python_type

    if python_type is list or python_type is dict:
        if python_type is list:
            raise ValueError("List type must have a specified element type")
        raise ValueError("Dict type must have a specified element type")

    if origin is not None:
        args = get_args(python_type)

        if origin is list:
            if not args:
                raise ValueError("List type must have a specified element type")
            item_type = args[0]
            if item_type is Any or item_type is object:
                raise ValueError("List elements cannot be Any or object type")

            if _is_container_type(item_type):
                raise ValueError(
                    "Nested containers are not allowed. Use Pydantic models for "
                    "complex nested structures."
                )

            item_schema = python_type_to_property_schema(
                item_type, globalns, "List item"
            )
            return FunctionPropertySchema(
                type="array", description=description, items=item_schema
            )

        elif origin is dict:
            raise ValueError(
                "Dict types are not supported in tool parameters. Use Pydantic "
                "models to define object structures."
            )

        elif origin is typing.Literal:
            allowed = get_args(python_type)
            if not allowed:
                raise ValueError("Literal must have at least one value")
            first = allowed[0]
            if isinstance(first, str):
                schema_type = "string"
            elif isinstance(first, bool):
                schema_type = "boolean"
            elif isinstance(first, int):
                schema_type = "integer"
            elif isinstance(first, float):
                schema_type = "number"
            else:
                raise TypeError(
                    f"Unsupported Literal value type: {type(first).__name__}"
                )
            type_check = type(first)
            if not all(isinstance(v, type_check) for v in allowed):
                raise TypeError(
                    f"Literal must have homogeneous values, got mixed types: {python_type}"
                )
            return FunctionPropertySchema(
                type=schema_type,
                description=description,
                enum=list(allowed),
            )

        elif origin is typing.Union or origin is types.UnionType:
            args = get_args(python_type)
            non_none_types = [arg for arg in args if arg is not type(None)]

            if len(non_none_types) == 1:
                main_type = non_none_types[0]
                if main_type is Any or main_type is object:
                    raise ValueError("Optional type cannot contain Any or object")
                return python_type_to_property_schema(main_type, globalns, description)
            raise ValueError(
                f"Union types with multiple non-None types are not supported: {python_type}"
            )

    raise TypeError(f"Unsupported type: {python_type}")


def function_definition_from_pydantic(
    model_class: type[BaseModel],
    *,
    name: str | None = None,
    description: str | None = None,
    globalns: dict[str, Any] | None = None,
) -> FunctionDefinitionSchema:
    """Build a whole tool definition from a single Pydantic model.

    The model's fields become the tool's parameters and its docstring becomes
    the tool description, so one declaration both tells the model how to call
    the tool and validates what comes back.
    """
    object_schema = pydantic_model_to_property_schema(
        model_class, globalns if globalns is not None else {}, description
    )
    return FunctionDefinitionSchema(
        name=name or model_class.__name__,
        description=object_schema.description,
        parameters=FunctionParametersSchema(
            type="object",
            properties=object_schema.properties or {},
            required=object_schema.required or [],
        ),
    )


def function_definition_from_signature(
    func: Callable[..., Any],
    *,
    name: str | None = None,
    description: str | None = None,
    parameter_descriptions: Mapping[str, str] | None = None,
) -> FunctionDefinitionSchema:
    """Build a tool definition from a callable's signature and type hints.

    Every parameter needs a type hint; ``parameter_descriptions`` supplies the
    per-parameter text (normally parsed from the docstring).
    """
    signature = inspect.signature(func)
    globalns: dict[str, Any] = getattr(func, "__globals__", {})
    type_hints = get_type_hints(func, globalns=globalns, localns={})
    properties: dict[str, FunctionPropertySchema] = {}
    required: list[str] = []

    for param_name, param in signature.parameters.items():
        if param_name == "self":
            continue
        param_type = type_hints.get(param_name)
        if param_type is None:
            raise TypeError(
                f"Parameter '{param_name}' in {func.__name__} must have a type hint"
            )
        if param_type is Any or param_type is object:
            raise ValueError(
                f"Parameter '{param_name}' uses '{param_type.__name__}' type, "
                "which is not allowed"
            )
        param_desc = (parameter_descriptions or {}).get(
            param_name
        ) or f"Parameter {param_name}"
        properties[param_name] = python_type_to_property_schema(
            param_type, globalns, param_desc
        )
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return FunctionDefinitionSchema(
        name=name or func.__name__,
        description=description or "(no description provided for this tool)",
        parameters=FunctionParametersSchema(
            type="object", properties=properties, required=required
        ),
    )


# Compilation: JSON Schema -> Pydantic validator


def _declared_types(prop: FunctionPropertySchema) -> list[str]:
    return list(prop.type) if isinstance(prop.type, list) else [prop.type]


def _non_null_types(prop: FunctionPropertySchema) -> list[str]:
    return [t for t in _declared_types(prop) if t != "null"]


def _allows_null(prop: FunctionPropertySchema) -> bool:
    return "null" in _declared_types(prop) or bool(prop.nullable)


def _numeric_bounds(prop: FunctionPropertySchema, *, integer: bool) -> dict[str, Any]:
    """Inclusive Pydantic bounds derived from the JSON Schema numeric keywords.

    ``exclusiveMinimum`` carries two meanings depending on draft: a boolean
    that makes ``minimum`` exclusive, or a number that *is* the exclusive
    bound. Both are accepted here.

    Integer properties are rounded inward, because JSON Schema bounds are
    numbers and an ``integer`` property routinely arrives as ``1.0``, which
    Pydantic refuses to use as a bound on an ``int`` field.
    """
    low = prop.minimum
    low_exclusive = False
    if isinstance(prop.exclusiveMinimum, bool):
        low_exclusive = prop.exclusiveMinimum
    elif prop.exclusiveMinimum is not None:
        low = prop.exclusiveMinimum
        low_exclusive = True

    high = prop.maximum
    high_exclusive = False
    if isinstance(prop.exclusiveMaximum, bool):
        high_exclusive = prop.exclusiveMaximum
    elif prop.exclusiveMaximum is not None:
        high = prop.exclusiveMaximum
        high_exclusive = True

    bounds: dict[str, Any] = {}
    if low is not None:
        if integer:
            bounds["ge"] = math.floor(low) + 1 if low_exclusive else math.ceil(low)
        else:
            bounds["gt" if low_exclusive else "ge"] = low
    if high is not None:
        if integer:
            bounds["le"] = math.ceil(high) - 1 if high_exclusive else math.floor(high)
        else:
            bounds["lt" if high_exclusive else "le"] = high
    if prop.multipleOf is not None:
        bounds["multiple_of"] = prop.multipleOf
    return bounds


def _constraint_kwargs(prop: FunctionPropertySchema, json_type: str) -> dict[str, Any]:
    """Field keywords for the constraint group that matches ``json_type``."""
    if json_type == "string":
        kwargs: dict[str, Any] = {}
        if prop.minLength is not None:
            kwargs["min_length"] = prop.minLength
        if prop.maxLength is not None:
            kwargs["max_length"] = prop.maxLength
        if prop.pattern is not None:
            kwargs["pattern"] = prop.pattern
        return kwargs
    if json_type in ("integer", "number"):
        return _numeric_bounds(prop, integer=json_type == "integer")
    if json_type == "array":
        kwargs = {}
        if prop.minItems is not None:
            kwargs["min_length"] = prop.minItems
        if prop.maxItems is not None:
            kwargs["max_length"] = prop.maxItems
        return kwargs
    return {}


def _unique_items(values: list[Any]) -> list[Any]:
    seen: list[Any] = []
    for value in values:
        if value in seen:
            raise ValueError("array items must be unique")
        seen.append(value)
    return values


def _literal_of(values: Sequence[Any]) -> Any | None:
    """``Literal[...]`` when every value is a homogeneous scalar, else ``None``."""
    kinds = {type(value) for value in values}
    if len(kinds) != 1 or not kinds <= {str, int, float, bool}:
        return None
    return Literal[tuple(values)]


def _restrict_to_values(annotation: Any, values: Sequence[Any]) -> Any:
    literal = _literal_of(values)
    if literal is not None:
        return literal
    allowed = tuple(values)

    def _check(value: Any) -> Any:
        if value not in allowed:
            raise ValueError(f"value must be one of {list(allowed)!r}")
        return value

    return Annotated[annotation, AfterValidator(_check)]


def _restricted_values(prop: FunctionPropertySchema) -> Sequence[Any]:
    if prop.const is not None:
        return [prop.const]
    if prop.enum is not None:
        return list(prop.enum)
    return []


def _union(parts: Sequence[Any]) -> Any:
    """Union of runtime annotations, built with ``|`` since the input is dynamic."""
    return reduce(or_, parts)


def _extra_value_annotation(additional: Mapping[str, Any]) -> Any | None:
    """Compile the schema an object declares for its extra values.

    MCP servers routinely describe a free-form map as ``{"type": "object",
    "additionalProperties": {"type": "string"}}``. That schema is compiled the
    same way as a named property, so a value of the wrong type in an extra key
    is rejected here instead of being forwarded to the server.

    Returns ``None`` when the schema constrains nothing an annotation could
    express: ``{}`` accepts every value, and so do the annotation-only keywords
    (``title``, ``description``, ``default``). Such a schema must not fall
    through to the ``string`` default used for a missing type, because that
    would reject extras the server is willing to take.
    """
    schema = MCPProperty.model_validate(additional)
    if (
        schema.type is None
        and schema.enum is None
        and schema.const is None
        and not (schema.anyOf or schema.oneOf or schema.allOf)
    ):
        return None
    return _annotation_for(cast_mcp_property_to_amrita(schema))


def _check_extra_value(adapter: TypeAdapter[Any], key: str, value: Any) -> None:
    """Reject a single extra value that does not match the declared schema."""
    try:
        adapter.validate_python(value)
    except ValidationError as exc:
        raise ValueError(
            f"additional property {key!r} does not match the declared "
            f"schema: {exc}"
        ) from exc


def _extra_value_checker(annotation: Any) -> Callable[[Any], Any]:
    """Build an after-validator rejecting extra values that miss ``annotation``.

    Pydantic's ``extra="allow"`` has no way to type the values it collects, so
    the declared schema is applied to ``__pydantic_extra__`` once the object has
    been validated.
    """
    adapter = TypeAdapter(annotation)

    def _check(model: Any) -> Any:
        for key, value in (model.__pydantic_extra__ or {}).items():
            _check_extra_value(adapter, key, value)
        return model

    return _check


def _object_annotation(prop: FunctionPropertySchema) -> Any:
    required = set(prop.required or ())
    fields: dict[str, Any] = {}
    for name, sub in (prop.properties or {}).items():
        annotation = _annotation_for(sub)
        if name in required:
            fields[name] = (annotation, ...)
        else:
            fields[name] = (annotation | None, sub.default)

    additional = prop.additionalProperties
    if additional is False:
        return create_model(
            "ToolArgumentObject", __config__=ConfigDict(extra="forbid"), **fields
        )

    model = create_model(
        "ToolArgumentObject", __config__=ConfigDict(extra="allow"), **fields
    )
    if not isinstance(additional, Mapping):
        return model

    extra_annotation = _extra_value_annotation(additional)
    if extra_annotation is None:
        return model
    return Annotated[model, AfterValidator(_extra_value_checker(extra_annotation))]


def _array_annotation(prop: FunctionPropertySchema) -> Any:
    if prop.items is None:
        return list[Any]
    return list[_annotation_for(prop.items)]


def _type_part(prop: FunctionPropertySchema, json_type: str) -> Any:
    if json_type == "object":
        return _object_annotation(prop)
    if json_type == "array":
        return _array_annotation(prop)
    return _JSON_SCALAR_TYPES.get(json_type, Any)


def _annotation_for(prop: FunctionPropertySchema) -> Any:
    """Compile one property schema into the Pydantic annotation that checks it."""
    declared = _non_null_types(prop)
    parts = [_type_part(prop, json_type) for json_type in declared]

    if not parts:
        annotation: Any = Any
    elif len(parts) == 1:
        annotation = parts[0]
    else:
        annotation = _union(parts)

    if len(declared) == 1:
        kwargs = _constraint_kwargs(prop, declared[0])
        if kwargs:
            annotation = Annotated[annotation, Field(**kwargs)]
        if declared[0] == "array" and prop.uniqueItems:
            annotation = Annotated[annotation, AfterValidator(_unique_items)]

    values = _restricted_values(prop)
    if values:
        annotation = _restrict_to_values(annotation, values)

    if _allows_null(prop):
        annotation = annotation | None
    return annotation


def _build_validator(params: FunctionParametersSchema) -> type[BaseModel]:
    required = set(params.required)
    fields: dict[str, Any] = {}
    for name, prop in params.properties.items():
        annotation = _annotation_for(prop)
        if name in required:
            fields[name] = (annotation, ...)
        else:
            fields[name] = (annotation | None, prop.default)
    return create_model("ToolArguments", __config__=ConfigDict(extra="allow"), **fields)


@cache
def _validator_for(schema_json: str) -> type[BaseModel]:
    return _build_validator(FunctionParametersSchema.model_validate_json(schema_json))


def compile_parameters_model(
    params: FunctionParametersSchema,
) -> type[BaseModel]:
    """Compile a parameter schema into the Pydantic model that validates it.

    Results are cached per schema, so a tool pays the build cost once.
    """
    return _validator_for(params.model_dump_json())


def validate_arguments(
    params: FunctionParametersSchema,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate model-produced arguments against a tool's parameter schema.

    Returns the arguments the tool should receive: values the model supplied
    are checked and coerced, and anything it left out stays left out, so a
    tool function's own defaults still apply. Raises
    :class:`pydantic.ValidationError` with a field-level message on a bad call;
    the agent loop converts that into an ``ERR: ...`` tool result, which is how
    the model learns to correct itself.
    """
    model = compile_parameters_model(params)
    validated = model.model_validate(dict(arguments))
    return validated.model_dump(exclude_unset=True)


__all__ = [
    "compile_parameters_model",
    "function_definition_from_pydantic",
    "function_definition_from_signature",
    "pydantic_model_to_property_schema",
    "python_type_to_property_schema",
    "validate_arguments",
]
