from __future__ import annotations

from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, Union, cast

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from amrita_core.utils import on_none

if TYPE_CHECKING:
    from amrita_core.agent.context import StrategyContext


T = TypeVar("T", str, int, float, bool, list, dict)  # JSON type
JSON_OBJECT_TYPE = Literal[
    "string",
    "number",
    "integer",
    "boolean",
    "array",
    "object",
    "null",
]


def cast_mcp_properties_to_amrita(
    property: dict[str, MCPProperty],
) -> dict[str, FunctionPropertySchema]:
    """
    Convert MCPProperty dictionary to FunctionPropertySchema objects
    """
    properties_dict: dict[str, FunctionPropertySchema] = {}

    for key, prop in deepcopy(property).items():
        # Convert MCP property to corresponding FunctionPropertySchema
        converted_prop = _convert_single_property(prop)
        properties_dict[key] = converted_prop

    return properties_dict


def _extract_types_from_anyof(prop: MCPProperty) -> list[JSON_OBJECT_TYPE]:
    """Extract type values from an anyOf list."""
    types: list[JSON_OBJECT_TYPE] = []
    if prop.anyOf:
        for sub in prop.anyOf:
            if sub.type:
                if isinstance(sub.type, list):
                    types.extend(cast(list[JSON_OBJECT_TYPE], sub.type))
                else:
                    types.append(cast(JSON_OBJECT_TYPE, sub.type))
    return types


def _convert_single_property(mcp_prop: MCPProperty) -> FunctionPropertySchema:
    """
    Convert a single MCPProperty to FunctionPropertySchema.
    Handles anyOf by extracting union types and merging constraints.
    """
    # Get basic attributes
    description = mcp_prop.description or "No description"

    # Determine the type(s)
    if mcp_prop.type:
        prop_type: JSON_OBJECT_TYPE | list[JSON_OBJECT_TYPE] = cast(
            JSON_OBJECT_TYPE | list[JSON_OBJECT_TYPE], mcp_prop.type
        )
    elif mcp_prop.anyOf:
        # Extract types from anyOf
        extracted = _extract_types_from_anyof(mcp_prop)
        prop_type = (
            extracted
            if len(extracted) > 1
            else (extracted[0] if extracted else "string")
        )
    else:
        prop_type = "string"  # default fallback

    # Prepare base parameters
    base_params: dict[str, Any] = {
        "type": prop_type,
        "description": description,
    }

    # If there are enum values, add to parameters
    if mcp_prop.enum is not None:
        base_params["enum"] = mcp_prop.enum

    # For anyOf, merge constraints from all subschemas (take first non-null entry)
    effective_prop = mcp_prop
    if mcp_prop.anyOf and not mcp_prop.type:
        # Pick the first non-null sub-schema for constraint extraction
        for sub in mcp_prop.anyOf:
            if sub.type and sub.type != "null" and sub.type != ["null"]:
                effective_prop = sub
                break

    types_to_check = prop_type if isinstance(prop_type, list) else [prop_type]
    # Filter out "null" when determining structural shape
    non_null_types = [t for t in types_to_check if t != "null"]
    has_object = "object" in non_null_types
    has_array = "array" in non_null_types

    if has_object:
        # Object type requires recursive conversion of its properties
        if effective_prop.properties:
            obj_properties = {}
            for key, sub_prop in effective_prop.properties.items():
                obj_properties[key] = _convert_single_property(sub_prop)
            base_params["properties"] = obj_properties
        if effective_prop.required:
            base_params["required"] = effective_prop.required

    elif has_array:
        if effective_prop.items:
            if isinstance(effective_prop.items, list):
                # Tuple validation: use first item schema
                base_params["items"] = _convert_single_property(effective_prop.items[0])
            else:
                base_params["items"] = _convert_single_property(effective_prop.items)
        if effective_prop.minItems is not None and effective_prop.minItems > 0:
            base_params["minItems"] = effective_prop.minItems
        if effective_prop.maxItems is not None and effective_prop.maxItems < 100:
            base_params["maxItems"] = effective_prop.maxItems
        if effective_prop.uniqueItems is not None:
            base_params["uniqueItems"] = effective_prop.uniqueItems

    # For numeric and boolean types, no additional fields are needed since FunctionPropertySchema
    # doesn't include minimum/maximum fields in the same way
    return FunctionPropertySchema(**base_params)


class MCPProperty(BaseModel):
    """Flexible MCP/JSON Schema property model supporting the full JSON Schema specification.

    This replaces the old rigid type-discriminated union (MCPPropertySchemaString,
    MCPPropertySchemaNumber, etc.) with a single model that handles all JSON Schema
    features including combinators (anyOf, oneOf, allOf) and flexible defaults.
    """

    #  Core type information
    type: str | list[str] | None = Field(
        default=None, description="Parameter type(s)", exclude_if=on_none
    )
    title: str | None = Field(
        default=None, description="Parameter title", exclude_if=on_none
    )
    description: str | None = Field(
        default=None, description="Parameter description", exclude_if=on_none
    )
    default: Any = Field(
        default=None, description="Parameter default value", exclude_if=on_none
    )
    enum: list[Any] | None = Field(
        default=None, description="Enumerated values", exclude_if=on_none
    )
    const: Any = Field(
        default=None,
        description="Constant value the parameter must equal",
        exclude_if=on_none,
    )

    #  String constraints
    pattern: str | None = Field(
        default=None, description="Regular expression pattern", exclude_if=on_none
    )
    minLength: int | None = Field(
        default=None, description="Minimum string length", exclude_if=on_none
    )
    maxLength: int | None = Field(
        default=None, description="Maximum string length", exclude_if=on_none
    )

    #  Numeric constraints
    minimum: float | int | None = Field(
        default=None, description="Minimum value (inclusive)", exclude_if=on_none
    )
    maximum: float | int | None = Field(
        default=None, description="Maximum value (inclusive)", exclude_if=on_none
    )
    exclusiveMinimum: bool | float | int | None = Field(
        default=None,
        description="Exclusive minimum (bool or numeric in draft 2020-12)",
        exclude_if=on_none,
    )
    exclusiveMaximum: bool | float | int | None = Field(
        default=None,
        description="Exclusive maximum (bool or numeric in draft 2020-12)",
        exclude_if=on_none,
    )
    multipleOf: float | int | None = Field(
        default=None, description="Value must be a multiple of this", exclude_if=on_none
    )

    #  Object constraints
    properties: dict[str, "MCPProperty"] | None = Field(
        default=None, description="Object property definitions", exclude_if=on_none
    )
    required: list[str] | None = Field(
        default=None, description="Required property names", exclude_if=on_none
    )
    additionalProperties: bool | dict[str, Any] | None = Field(
        default=None,
        description="Allow additional properties or define their schema",
        exclude_if=on_none,
    )

    #  Array constraints
    items: Union["MCPProperty", list["MCPProperty"]] | None = (  # noqa: UP007
        Field(  # Because X|Y is invalid here, we use Union.
            default=None, description="Array item schema(s)", exclude_if=on_none
        )
    )
    minItems: int | None = Field(
        default=None, description="Minimum array length", exclude_if=on_none
    )
    maxItems: int | None = Field(
        default=None, description="Maximum array length", exclude_if=on_none
    )
    uniqueItems: bool | None = Field(
        default=None,
        description="Whether array items must be unique",
        exclude_if=on_none,
    )

    #  JSON Schema combinators
    anyOf: list["MCPProperty"] | None = Field(
        default=None,
        description="Any of the given schemas must validate",
        exclude_if=on_none,
    )
    oneOf: list["MCPProperty"] | None = Field(
        default=None,
        description="Exactly one of the given schemas must validate",
        exclude_if=on_none,
    )
    allOf: list["MCPProperty"] | None = Field(
        default=None,
        description="All of the given schemas must validate",
        exclude_if=on_none,
    )

    #  Format
    format: str | None = Field(
        default=None,
        description="Semantic format hint (date, email, uri, etc.)",
        exclude_if=on_none,
    )


MCP_OBJECT_TYPE = MCPProperty  # For backward compatibility


class MCPToolSchema(BaseModel):
    """Define the structure of MCP tools"""

    name: str = Field(..., description="Tool name")
    description: str = Field("No description", description="Tool description")
    inputSchema: MCPProperty = Field(
        ..., description="Tool parameter definition (JSON Schema)"
    )


class FunctionPropertySchema(BaseModel, Generic[T]):
    """Property for validating function arguments"""

    type: Literal[JSON_OBJECT_TYPE] | list[JSON_OBJECT_TYPE] = Field(
        ..., description="Parameter type"
    )
    description: str = Field("No description", description="Parameter description")
    enum: list[T] | None = Field(
        default=None, description="Enumerated parameters", exclude_if=on_none
    )
    const: Any | None = Field(
        default=None,
        description="Constant value that the parameter must equal",
        exclude_if=on_none,
    )
    default: Any | None = Field(
        default=None, description="Default value for the parameter", exclude_if=on_none
    )
    minimum: float | None = Field(
        default=None,
        description="Minimum value (inclusive) for numeric types",
        exclude_if=on_none,
    )
    maximum: float | None = Field(
        default=None,
        description="Maximum value (inclusive) for numeric types",
        exclude_if=on_none,
    )
    exclusiveMinimum: bool | None = Field(
        default=None,
        description="Whether value must be greater than minimum (default false)",
        exclude_if=on_none,
    )
    exclusiveMaximum: bool | None = Field(
        default=None,
        description="Whether value must be less than maximum (default false)",
        exclude_if=on_none,
    )
    multipleOf: float | None = Field(
        default=None,
        description="Value must be a multiple of this number",
        exclude_if=on_none,
    )
    minLength: int | None = Field(
        default=None,
        description="Minimum string length (inclusive)",
        exclude_if=on_none,
    )
    maxLength: int | None = Field(
        default=None,
        description="Maximum string length (inclusive)",
        exclude_if=on_none,
    )
    pattern: str | None = Field(
        default=None,
        description="Regular expression that string must match",
        exclude_if=on_none,
    )
    properties: dict[str, FunctionPropertySchema] | None = Field(
        default=None,
        description="Parameter property definitions, only valid when parameter type is object",
        exclude_if=on_none,
    )
    items: FunctionPropertySchema | None = Field(
        default=None,
        description="Used only when type='array', defines array element type",
        exclude_if=on_none,
    )
    minItems: int | None = Field(
        default=None,
        description="Used only when type='array', defines minimum array length",
        exclude_if=on_none,
    )
    maxItems: int | None = Field(
        default=None,
        description="Used only when type='array', defines maximum number of array elements",
        exclude_if=on_none,
    )
    uniqueItems: bool | None = Field(
        default=None,
        description="Whether array elements must be unique, when type is array, this parameter defaults to False",
        exclude_if=on_none,
    )
    required: list[str] | None = Field(
        default=None,
        description="Parameter property definitions, only valid when parameter type is object",
        exclude_if=on_none,
    )
    additionalProperties: bool | dict[str, Any] | None = Field(
        default=None,
        description="Whether object allows additional properties or schema for additional properties",
        exclude_if=on_none,
    )
    format: str | None = Field(
        default=None,
        description="String format such as date, time, datetime, email, uri, uuid, etc.",
        exclude_if=on_none,
    )
    nullable: bool | None = Field(
        default=None,
        description="Whether parameter can be null (equivalent to type: [original_type, 'null'])",
        exclude_if=on_none,
    )

    @model_validator(mode="after")
    def validator(self) -> Self:
        # Handle type as list (union types)
        types_to_check = self.type if isinstance(self.type, list) else [self.type]

        # Check if we have object or array types
        has_object = "object" in types_to_check
        has_array = "array" in types_to_check
        has_string = "string" in types_to_check
        has_numeric = any(t in types_to_check for t in ["number", "integer"])
        has_boolean = "boolean" in types_to_check

        # Object type validation
        if has_object:
            if self.properties is None:
                raise ValueError("When type is object, properties must be set.")
            elif self.required is None:
                self.required = []
            if any(
                i is not None
                for i in (self.maxItems, self.minItems, self.uniqueItems, self.items)
            ):
                raise ValueError(
                    "When type includes object, `maxItems`,`minItems`,`uniqueItems`,`items` must be None."
                )
            if any(
                i is not None
                for i in (
                    self.minLength,
                    self.maxLength,
                    self.pattern,
                    self.format,
                    self.minimum,
                    self.maximum,
                    self.exclusiveMinimum,
                    self.exclusiveMaximum,
                    self.multipleOf,
                )
            ):
                raise ValueError(
                    "When type includes object, string and numeric constraints must be None."
                )

        # Array type validation
        elif has_array:
            if self.items is None:
                raise ValueError("When type is array, items must be set.")
            elif self.minItems is not None and self.minItems < 0:
                raise ValueError("minItems must be greater than or equal to 0.")
            elif self.maxItems is not None and self.maxItems < 0:
                raise ValueError("maxItems must be greater than or equal to 0.")
            elif (
                self.maxItems is not None
                and self.minItems is not None
                and self.maxItems < self.minItems
            ):
                raise ValueError("maxItems must be greater than or equal to minItems.")
            elif self.uniqueItems is None:
                self.uniqueItems = False
            if any(
                i is not None
                for i in (
                    self.minLength,
                    self.maxLength,
                    self.pattern,
                    self.format,
                    self.minimum,
                    self.maximum,
                    self.exclusiveMinimum,
                    self.exclusiveMaximum,
                    self.multipleOf,
                    self.properties,
                )
            ):
                raise ValueError(
                    "When type includes array, string, numeric, and object constraints must be None."
                )

        # String type validation
        if has_string:
            if self.minLength is not None and self.minLength < 0:
                raise ValueError("minLength must be greater than or equal to 0.")
            elif self.maxLength is not None and self.maxLength < 0:
                raise ValueError("maxLength must be greater than or equal to 0.")
            elif (
                self.maxLength is not None
                and self.minLength is not None
                and self.maxLength < self.minLength
            ):
                raise ValueError(
                    "maxLength must be greater than or equal to minLength."
                )
            if any(
                i is not None
                for i in (
                    self.minimum,
                    self.maximum,
                    self.exclusiveMinimum,
                    self.exclusiveMaximum,
                    self.multipleOf,
                    self.items,
                    self.minItems,
                    self.maxItems,
                    self.uniqueItems,
                    self.properties,
                )
            ):
                raise ValueError(
                    "When type includes string, numeric and array constraints must be None."
                )

        # Numeric type validation
        if has_numeric:
            if (
                self.minimum is not None
                and self.maximum is not None
                and self.minimum > self.maximum
            ):
                raise ValueError("minimum must be less than or equal to maximum.")
            if self.multipleOf is not None and self.multipleOf <= 0:
                raise ValueError("multipleOf must be greater than 0.")
            if any(
                i is not None
                for i in (
                    self.minLength,
                    self.maxLength,
                    self.pattern,
                    self.format,
                    self.items,
                    self.minItems,
                    self.maxItems,
                    self.uniqueItems,
                    self.properties,
                )
            ):
                raise ValueError(
                    "When type includes numeric, string and array constraints must be None."
                )

        # Boolean type validation
        if has_boolean:
            if any(
                i is not None
                for i in (
                    self.minLength,
                    self.maxLength,
                    self.pattern,
                    self.format,
                    self.minimum,
                    self.maximum,
                    self.exclusiveMinimum,
                    self.exclusiveMaximum,
                    self.multipleOf,
                    self.items,
                    self.minItems,
                    self.maxItems,
                    self.uniqueItems,
                    self.properties,
                )
            ):
                raise ValueError(
                    "When type includes boolean, string, numeric, and array constraints must be None."
                )

        return self


class FunctionParametersSchema(BaseModel):
    """Validate function parameter structure"""

    type: Literal["object"] = Field(..., description="Parameter type")
    properties: dict[str, FunctionPropertySchema] = Field(
        default_factory=dict, description="Parameter property definitions"
    )

    required: list[str] = Field(
        default_factory=list, description="List of required parameters"
    )


class FunctionDefinitionSchema(BaseModel):
    """Validate function definition structure"""

    name: str = Field(..., description="Function name")
    description: str = Field(..., description="Function description")
    parameters: FunctionParametersSchema = Field(
        ..., description="Function parameter definition"
    )


class ToolFunctionSchema(BaseModel):
    """Validate complete function field structure"""

    function: FunctionDefinitionSchema = Field(..., description="Function definition")
    type: Literal["function"] = "function"
    strict: bool = Field(default=False, description="Whether in strict mode")


ToolChoice = Literal["none", "auto", "required"] | ToolFunctionSchema


@dataclass
class ToolContext:
    data: dict[str, Any] = field()
    ctx: "StrategyContext" = field()


class ToolData(BaseModel):
    """Data model for registering Tools"""

    data: ToolFunctionSchema = Field(..., description="Tool metadata")
    func: (
        Callable[[dict[str, Any]], Awaitable[str]]
        | Callable[[ToolContext], Awaitable[str | None]]
    ) = Field(..., description="Tool function")
    custom_run: bool = Field(
        default=False,
        description="Whether to customize execution; if enabled, passes Context class instead of dict and does not enforce return value.",
    )
    enable_if: Callable[[], bool] = Field(
        default=lambda: True,
        description="Whether to enable this tool",
    )
