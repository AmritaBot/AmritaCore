from __future__ import annotations

from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from ..hook.event import Event
from ..hook.matcher import Matcher

T = TypeVar("T", str, int, float, bool, list, dict)  # JSON type
JOT_T = TypeVar(
    "JOT_T",
    Literal["string"],
    Literal["number"],
    Literal["integer"],
    Literal["boolean"],
    Literal["array"],
    Literal["object"],
)
NUM_T = TypeVar("NUM_T", int, float)
JSON_OBJECT_TYPE = Literal[
    "string",
    "number",
    "integer",
    "boolean",
    "array",
    "object",
]


def on_none(value: Any | None) -> bool:
    """Used for Pydantic's exclude_if

    Args:
        value (Any | None): Value to check

    Returns:
        bool: Returns True when Value is None
    """
    return value is None


def cast_mcp_properties_to_openai(
    property: dict[str, MCP_OBJECT_TYPE],
) -> dict[str, FunctionPropertySchema]:
    """
    Convert MCPPropertySchemaObject dictionary to FunctionPropertySchema objects
    """
    properties_dict: dict[str, FunctionPropertySchema] = {}

    for key, prop in deepcopy(property).items():
        # Convert MCP property type to corresponding FunctionPropertySchema
        converted_prop = _convert_single_property(prop)
        properties_dict[key] = converted_prop

    return properties_dict


def _convert_single_property(mcp_prop: MCP_OBJECT_TYPE) -> FunctionPropertySchema:
    """
    Convert a single MCP_PROPERTY to FunctionPropertySchema
    """
    # Get basic attributes
    description = getattr(
        mcp_prop,
        "description",
        "No description",
    )
    prop_type: JSON_OBJECT_TYPE = mcp_prop.type

    # Prepare base parameters
    base_params = {
        "type": prop_type,
        "description": description,
    }

    # If there are enum values, add to parameters
    if hasattr(mcp_prop, "enum") and mcp_prop.enum is not None:
        base_params["enum"] = mcp_prop.enum

    if isinstance(mcp_prop, MCPPropertySchemaObject):
        # Object type requires recursive conversion of its properties
        if hasattr(mcp_prop, "properties") and mcp_prop.properties:
            obj_properties = {}
            for key, sub_prop in mcp_prop.properties.items():
                obj_properties[key] = _convert_single_property(sub_prop)
            base_params["properties"] = obj_properties
        if hasattr(mcp_prop, "required") and mcp_prop.required:
            base_params["required"] = mcp_prop.required

    elif isinstance(mcp_prop, MCPPropertySchemaArray):
        if hasattr(mcp_prop, "items"):
            base_params["items"] = _convert_single_property(mcp_prop.items)
        if hasattr(mcp_prop, "minItems") and mcp_prop.minItems > 0:
            base_params["minItems"] = mcp_prop.minItems
        if hasattr(mcp_prop, "maxItems") and mcp_prop.maxItems < 100:
            base_params["maxItems"] = mcp_prop.maxItems
        if hasattr(mcp_prop, "uniqueItems"):
            base_params["uniqueItems"] = mcp_prop.uniqueItems

    # For numeric and boolean types, no additional fields are needed since FunctionPropertySchema doesn't include minimum/maximum fields
    return FunctionPropertySchema(**base_params)


class MCPPropertySchema(BaseModel, Generic[JOT_T]):
    """Base structure definition for MCP properties"""

    type: JOT_T = Field(..., description="Parameter type")
    title: str = Field("NO_TITLE", description="Parameter title")
    description: str = Field(
        default="No description", description="Parameter description"
    )
    default: None = Field(
        default=None, description="Parameter default value", exclude_if=on_none
    )
    enum: list[str | int | float] | None = Field(
        default=None, description="Enumerated parameters", exclude_if=on_none
    )


class MCPPropertySchemaString(MCPPropertySchema[Literal["string"]]):
    """MCP property structure for validating string types"""

    pattern: str | None = Field(
        default=None, description="Regular expression", exclude_if=on_none
    )
    minLength: int = Field(default=0, description="Minimum length")
    maxLength: int = Field(default=100, description="Maximum length")


class MCPPropertySchemaNumeric(MCPPropertySchema[JOT_T], Generic[JOT_T, NUM_T]):
    """MCP property structure for validating numeric types"""

    minimum: NUM_T | None = Field(
        default=None, description="Minimum value", exclude_if=on_none
    )
    maximum: NUM_T | None = Field(
        default=None, description="Maximum value", exclude_if=on_none
    )
    exclusiveMinimum: bool | None = Field(
        default=None,
        description="Whether minimum value is exclusive (i.e. 'left open interval')",
        exclude_if=on_none,
    )
    exclusiveMaximum: bool | None = Field(
        default=None,
        description="Whether maximum value is exclusive (i.e. 'right open interval')",
        exclude_if=on_none,
    )


class MCPPropertySchemaInteger(MCPPropertySchemaNumeric[Literal["integer"], int]):
    """MCP property structure for validating integer types"""


class MCPPropertySchemaNumber(MCPPropertySchemaNumeric[Literal["number"], float]):
    """MCP property structure for validating floating point types"""


class MCPPropertySchemaObject(MCPPropertySchema[Literal["object"]]):
    """MCP property structure for validating object types"""

    properties: dict[str, MCP_OBJECT_TYPE] = Field(
        ..., description="Parameter property definitions", exclude_if=on_none
    )
    required: list[str] = Field(
        default_factory=list, description="List of required parameters"
    )

    @model_validator(mode="after")
    def validator(self) -> Self:
        if self.required:
            for req in self.required:
                if req not in self.properties:
                    raise ValueError(
                        f"Required property '{req}' not found in properties."
                    )
        return self


class MCPPropertySchemaArray(MCPPropertySchema[Literal["array"]]):
    """MCP property structure for validating array types"""

    items: MCP_OBJECT_TYPE = Field(
        ..., description="Parameter property definition", exclude_if=on_none
    )
    maxItems: int = Field(default=100, description="Maximum number of elements")
    minItems: int = Field(default=0, description="Minimum number of elements")
    uniqueItems: bool = Field(
        default=False,
        description="Whether array elements must be unique, when type is array, this parameter defaults to False",
    )


class MCPPropertySchemaBoolean(MCPPropertySchema[Literal["boolean"]]):
    """MCP property structure for validating boolean types"""


MCP_OBJECT_TYPE = (
    MCPPropertySchemaObject
    | MCPPropertySchemaString
    | MCPPropertySchemaNumber
    | MCPPropertySchemaInteger
    | MCPPropertySchemaArray
    | MCPPropertySchemaBoolean
)


class MCPToolSchema(BaseModel):
    """Define the structure of MCP tools"""

    name: str = Field(..., description="Tool name")
    description: str = Field("No description", description="Tool description")
    inputSchema: MCPPropertySchemaObject = Field(
        ..., description="Tool parameter definition"
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

    @model_validator(mode="after")
    def validator(self) -> Self:
        if self.type == "object":
            if self.properties is None:
                raise ValueError("When type is object, properties must be set.")
            elif self.required is None:
                self.required = []
            if any(
                i is not None
                for i in (self.maxItems, self.minItems, self.uniqueItems, self.items)
            ):
                raise ValueError(
                    "When type is object, `maxItems`,`minItems`,`uniqueItems`,`Items` must be None."
                )
        elif self.type == "array":
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

        return self


class FunctionParametersSchema(BaseModel):
    """Validate function parameter structure"""

    type: Literal["object"] = Field(..., description="Parameter type")
    properties: dict[str, FunctionPropertySchema] | None = Field(
        default=None, description="Parameter property definitions", exclude_if=on_none
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
    event: Event = field()
    matcher: Matcher = field()


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
