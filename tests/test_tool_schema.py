"""Tests for the orthogonal tool schema layer: projection and compilation."""

from __future__ import annotations

from typing import Any, Literal

import pytest
from pydantic import BaseModel, Field, ValidationError

from amrita_core.tools.manager import ToolsManager, simple_tool
from amrita_core.tools.models import (
    FunctionParametersSchema,
    FunctionPropertySchema,
    MCPProperty,
    cast_mcp_properties_to_amrita,
)
from amrita_core.tools.schema import (
    compile_parameters_model,
    function_definition_from_pydantic,
    validate_arguments,
)


def _params(**properties: FunctionPropertySchema) -> FunctionParametersSchema:
    return FunctionParametersSchema(type="object", properties=properties)


class TestProjection:
    """Pydantic -> FunctionDefinitionSchema."""

    def test_field_constraints_survive_projection(self):
        class Args(BaseModel):
            count: int = Field(description="How many", ge=1, le=10)
            name: str = Field(description="Name", min_length=2, max_length=8)
            slug: str = Field(description="Slug", pattern="^[a-z]+$")
            ratio: float = Field(description="Ratio", multiple_of=0.5)

        params = function_definition_from_pydantic(Args).parameters
        assert params.properties["count"].minimum == 1
        assert params.properties["count"].maximum == 10
        assert params.properties["name"].minLength == 2
        assert params.properties["name"].maxLength == 8
        assert params.properties["slug"].pattern == "^[a-z]+$"
        assert params.properties["ratio"].multipleOf == 0.5

    def test_defaults_and_requiredness(self):
        class Args(BaseModel):
            required_one: int = Field(description="Required")
            flagged: bool = Field(default=False, description="Optional flag")
            sized: int = Field(default=7, description="Optional number")

        params = function_definition_from_pydantic(Args).parameters
        assert params.required == ["required_one"]
        assert params.properties["flagged"].default is False
        assert params.properties["sized"].default == 7

    def test_optional_annotation_marks_nullable_only_when_required(self):
        class Args(BaseModel):
            must_allow_null: str | None = Field(description="Required, nullable")
            may_omit: str | None = Field(default=None, description="Optional")

        params = function_definition_from_pydantic(Args).parameters
        assert params.properties["must_allow_null"].nullable is True
        assert params.required == ["must_allow_null"]
        assert params.properties["may_omit"].nullable is None

    def test_definition_uses_docstring_as_description(self):
        class Args(BaseModel):
            """Look something up."""

            key: str = Field(description="The key")

        definition = function_definition_from_pydantic(Args)
        assert definition.name == "Args"
        assert definition.description == "Look something up."

    def test_name_and_description_override(self):
        class Args(BaseModel):
            key: str = Field(description="The key")

        definition = function_definition_from_pydantic(
            Args, name="lookup", description="Custom"
        )
        assert definition.name == "lookup"
        assert definition.description == "Custom"


class TestCompilation:
    """FunctionParametersSchema -> validating Pydantic model."""

    def test_omitted_optional_stays_omitted(self):
        params = _params(
            a=FunctionPropertySchema(type="integer", description="a"),
            b=FunctionPropertySchema(type="integer", description="b"),
        )
        params.required = ["a"]
        assert validate_arguments(params, {"a": 1}) == {"a": 1}

    def test_extra_keys_pass_through(self):
        params = _params(a=FunctionPropertySchema(type="integer", description="a"))
        params.required = ["a"]
        assert validate_arguments(params, {"a": 1, "extra": "kept"}) == {
            "a": 1,
            "extra": "kept",
        }

    def test_missing_required_is_rejected(self):
        params = _params(a=FunctionPropertySchema(type="integer", description="a"))
        params.required = ["a"]
        with pytest.raises(ValidationError, match="Field required"):
            validate_arguments(params, {})

    def test_string_constraints_are_enforced(self):
        params = _params(
            name=FunctionPropertySchema(
                type="string",
                description="n",
                pattern="^[a-z]+$",
                minLength=2,
            )
        )
        params.required = ["name"]
        assert validate_arguments(params, {"name": "abc"}) == {"name": "abc"}
        with pytest.raises(ValidationError, match="pattern"):
            validate_arguments(params, {"name": "ABC"})
        with pytest.raises(ValidationError, match="at least 2 characters"):
            validate_arguments(params, {"name": "a"})

    def test_integer_bounds_are_rounded_inward(self):
        params = _params(
            n=FunctionPropertySchema(
                type="integer", description="n", minimum=1.5, maximum=2.5
            )
        )
        params.required = ["n"]
        assert validate_arguments(params, {"n": 2}) == {"n": 2}
        with pytest.raises(ValidationError):
            validate_arguments(params, {"n": 1})
        with pytest.raises(ValidationError):
            validate_arguments(params, {"n": 3})

    def test_numeric_exclusive_bounds(self):
        params = _params(
            n=FunctionPropertySchema(
                type="number", description="n", exclusiveMinimum=0, maximum=1
            )
        )
        params.required = ["n"]
        assert validate_arguments(params, {"n": 0.5}) == {"n": 0.5}
        with pytest.raises(ValidationError):
            validate_arguments(params, {"n": 0})

    def test_boolean_exclusive_bound_applies_to_minimum(self):
        params = _params(
            n=FunctionPropertySchema(
                type="number", description="n", minimum=0, exclusiveMinimum=True
            )
        )
        params.required = ["n"]
        with pytest.raises(ValidationError):
            validate_arguments(params, {"n": 0})

    def test_multiple_of_is_enforced(self):
        params = _params(
            n=FunctionPropertySchema(type="number", description="n", multipleOf=0.5)
        )
        params.required = ["n"]
        assert validate_arguments(params, {"n": 1.5}) == {"n": 1.5}
        with pytest.raises(ValidationError):
            validate_arguments(params, {"n": 0.3})

    def test_enum_and_const_are_enforced(self):
        params = _params(
            mode=FunctionPropertySchema(
                type="string", description="m", enum=["a", "b"]
            ),
            kind=FunctionPropertySchema(type="integer", description="k", const=1),
        )
        params.required = ["mode", "kind"]
        assert validate_arguments(params, {"mode": "a", "kind": 1}) == {
            "mode": "a",
            "kind": 1,
        }
        with pytest.raises(ValidationError):
            validate_arguments(params, {"mode": "z", "kind": 1})
        with pytest.raises(ValidationError):
            validate_arguments(params, {"mode": "a", "kind": 2})

    def test_mixed_enum_falls_back_to_membership_check(self):
        params = _params(
            value=FunctionPropertySchema(type="string", description="v", enum=["a", 1])
        )
        params.required = ["value"]
        assert validate_arguments(params, {"value": "a"}) == {"value": "a"}
        with pytest.raises(ValidationError, match="must be one of"):
            validate_arguments(params, {"value": "z"})
        # The declared type still wins: a non-string enum member is unreachable.
        with pytest.raises(ValidationError, match="valid string"):
            validate_arguments(params, {"value": 1})

    def test_array_bounds_and_uniqueness(self):
        item = FunctionPropertySchema(type="string", description="i")
        params = _params(
            tags=FunctionPropertySchema(
                type="array", description="t", items=item, minItems=1, maxItems=2
            ),
            uniq=FunctionPropertySchema(
                type="array", description="u", items=item, uniqueItems=True
            ),
        )
        params.required = ["tags", "uniq"]
        assert validate_arguments(params, {"tags": ["a"], "uniq": ["a", "b"]}) == {
            "tags": ["a"],
            "uniq": ["a", "b"],
        }
        with pytest.raises(ValidationError):
            validate_arguments(params, {"tags": [], "uniq": ["a"]})
        with pytest.raises(ValidationError):
            validate_arguments(params, {"tags": ["a"], "uniq": ["a", "a"]})

    def test_nested_object(self):
        inner = FunctionPropertySchema(
            type="object",
            description="inner",
            properties={"n": FunctionPropertySchema(type="integer", description="n")},
            required=["n"],
        )
        params = _params(payload=inner)
        params.required = ["payload"]
        assert validate_arguments(params, {"payload": {"n": 1}}) == {
            "payload": {"n": 1}
        }
        with pytest.raises(ValidationError):
            validate_arguments(params, {"payload": {}})

    def test_additional_properties_false_forbids_extra(self):
        inner = FunctionPropertySchema(
            type="object",
            description="inner",
            properties={"n": FunctionPropertySchema(type="integer", description="n")},
            required=["n"],
            additionalProperties=False,
        )
        params = _params(payload=inner)
        params.required = ["payload"]
        with pytest.raises(ValidationError):
            validate_arguments(params, {"payload": {"n": 1, "junk": 2}})

    def test_nullable_property_accepts_none(self):
        params = _params(
            note=FunctionPropertySchema(type="string", description="n", nullable=True)
        )
        params.required = ["note"]
        assert validate_arguments(params, {"note": None}) == {"note": None}

    def test_multi_type_property_accepts_either(self):
        params = _params(
            value=FunctionPropertySchema(type=["string", "integer"], description="v")
        )
        params.required = ["value"]
        assert validate_arguments(params, {"value": "a"}) == {"value": "a"}
        assert validate_arguments(params, {"value": 1}) == {"value": 1}
        with pytest.raises(ValidationError):
            validate_arguments(params, {"value": 1.5})

    def test_literal_type_from_enum_round_trips(self):
        params = _params(
            mode=FunctionPropertySchema(
                type="string", description="m", enum=["analyze", "plan"]
            )
        )
        params.required = ["mode"]
        with pytest.raises(ValidationError):
            validate_arguments(params, {"mode": "execute"})

    def test_compiled_model_is_cached_per_schema(self):
        params = _params(a=FunctionPropertySchema(type="integer", description="a"))
        assert compile_parameters_model(params) is compile_parameters_model(params)


class TestMcpConversion:
    """JSON Schema from MCP servers keeps its constraints."""

    def test_scalar_constraints_survive(self):
        raw: dict[str, dict[str, Any]] = {
            "count": {"type": "integer", "minimum": 1, "maximum": 10},
            "name": {"type": "string", "pattern": "^[a-z]+$", "minLength": 2},
            "ratio": {"type": "number", "multipleOf": 0.5, "exclusiveMinimum": 0},
        }
        converted = cast_mcp_properties_to_amrita(
            {key: MCPProperty.model_validate(value) for key, value in raw.items()}
        )
        assert converted["count"].minimum == 1
        assert converted["count"].maximum == 10
        assert converted["name"].pattern == "^[a-z]+$"
        assert converted["name"].minLength == 2
        assert converted["ratio"].multipleOf == 0.5
        assert converted["ratio"].exclusiveMinimum == 0

    def test_converted_constraints_are_enforced(self):
        converted = cast_mcp_properties_to_amrita(
            {
                "count": MCPProperty.model_validate(
                    {"type": "integer", "minimum": 5, "description": "c"}
                )
            }
        )
        params = FunctionParametersSchema(
            type="object", properties=converted, required=["count"]
        )
        assert validate_arguments(params, {"count": 5}) == {"count": 5}
        with pytest.raises(ValidationError):
            validate_arguments(params, {"count": 4})

    def test_object_additional_properties_is_carried(self):
        converted = cast_mcp_properties_to_amrita(
            {
                "payload": MCPProperty.model_validate(
                    {
                        "type": "object",
                        "properties": {"n": {"type": "integer"}},
                        "additionalProperties": False,
                    }
                )
            }
        )
        assert converted["payload"].additionalProperties is False

    def test_free_form_object_without_properties(self):
        converted = cast_mcp_properties_to_amrita(
            {
                "metadata": MCPProperty.model_validate(
                    {
                        "type": "object",
                        "description": "Free-form map",
                        "additionalProperties": {"type": "string"},
                    }
                )
            }
        )
        assert converted["metadata"].properties == {}
        assert converted["metadata"].required == []
        assert converted["metadata"].additionalProperties == {"type": "string"}

    def test_free_form_object_is_usable(self):
        converted = cast_mcp_properties_to_amrita(
            {"metadata": MCPProperty.model_validate({"type": "object"})}
        )
        params = FunctionParametersSchema(
            type="object", properties=converted, required=["metadata"]
        )
        assert validate_arguments(params, {"metadata": {"any": 1}}) == {
            "metadata": {"any": 1}
        }

    def test_schema_valued_additional_properties_are_enforced(self):
        converted = cast_mcp_properties_to_amrita(
            {
                "metadata": MCPProperty.model_validate(
                    {"type": "object", "additionalProperties": {"type": "string"}}
                )
            }
        )
        params = FunctionParametersSchema(
            type="object", properties=converted, required=["metadata"]
        )
        assert validate_arguments(params, {"metadata": {"a": "x"}}) == {
            "metadata": {"a": "x"}
        }
        with pytest.raises(ValidationError):
            validate_arguments(params, {"metadata": {"a": 1}})

    def test_empty_additional_properties_schema_accepts_any_value(self):
        converted = cast_mcp_properties_to_amrita(
            {
                "metadata": MCPProperty.model_validate(
                    {"type": "object", "additionalProperties": {}}
                )
            }
        )
        params = FunctionParametersSchema(
            type="object", properties=converted, required=["metadata"]
        )
        payload = {"a": [1, 2], "b": None, "c": {"nested": True}}
        assert validate_arguments(params, {"metadata": payload}) == {
            "metadata": payload
        }


class TestSimpleToolStillWorks:
    """The signature path keeps its behaviour after moving to the shared module."""

    @pytest.mark.asyncio
    async def test_python_default_survives_validation(self):
        @simple_tool
        def add_with_default(a: int, b: int = 5) -> int:
            """Add two numbers.

            Args:
                a (int): The first number.
                b (int): The second number.
            """
            return a + b

        tool = ToolsManager().get_tool("add_with_default")
        assert tool is not None
        params = tool.data.function.parameters
        assert params.required == ["a"]
        validated = validate_arguments(params, {"a": 1})
        assert validated == {"a": 1}
        assert await add_with_default(validated) == "6"

    @pytest.mark.asyncio
    async def test_literal_param_still_generates_enum(self):
        @simple_tool
        def pick_axis(axis: Literal["x", "y"]) -> str:
            """Pick an axis.

            Args:
                axis (Literal): The axis to pick.
            """
            return axis

        tool = ToolsManager().get_tool("pick_axis")
        assert tool is not None
        assert tool.data.function.parameters.properties["axis"].enum == ["x", "y"]
