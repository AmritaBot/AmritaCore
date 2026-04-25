import asyncio
import inspect
import json
import re
import types
import typing
from asyncio import iscoroutinefunction
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, get_args, get_origin, get_type_hints, overload

from pydantic import BaseModel
from typing_extensions import Self

from amrita_core.threadsafe import ContextThreadsafe

from .models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
    ToolContext,
    ToolData,
    ToolFunctionSchema,
)

T = typing.TypeVar("T")


class MultiToolsManager(ContextThreadsafe):
    _models: dict[str, ToolData]
    _disabled_tools: set[
        str
    ]  # Disabled tools, has_tool and get_tool will not return disabled tools

    def __init__(self):
        super().__init__()
        self._models = {}
        self._disabled_tools = set()

    def has_tool(self, name: str) -> bool:
        return False if name in self._disabled_tools else name in self._models

    @overload
    def get_tool(self, name: str) -> ToolData | None: ...
    @overload
    def get_tool(self, name: str, default: T) -> ToolData | T: ...
    def get_tool(self, name: str, default: T = None) -> ToolData | T | None:
        if not self.has_tool(name):
            return default
        tool: ToolData = self._models[name]
        return tool if tool.enable_if() else default

    @overload
    def get_tool_meta(self, name: str) -> ToolFunctionSchema | None: ...
    @overload
    def get_tool_meta(self, name: str, default: T) -> ToolFunctionSchema | T: ...
    def get_tool_meta(
        self, name: str, default: T | None = None
    ) -> ToolFunctionSchema | None | T:
        func_data = self.get_tool(name)
        if func_data is None:
            return default
        if isinstance(func_data, ToolData):
            return func_data.data
        return default

    @overload
    def get_tool_func(
        self, name: str, default: T
    ) -> (
        Callable[[dict[str, Any]], Awaitable[str]]
        | Callable[[ToolContext], Awaitable[str | None]]
        | T
    ): ...
    @overload
    def get_tool_func(
        self,
        name: str,
    ) -> (
        Callable[[dict[str, Any]], Awaitable[str]]
        | Callable[[ToolContext], Awaitable[str | None]]
        | None
    ): ...
    def get_tool_func(
        self, name: str, default: T | None = None
    ) -> (
        Callable[[dict[str, Any]], Awaitable[str]]
        | Callable[[ToolContext], Awaitable[str | None]]
        | None
        | T
    ):
        func_data = self.get_tool(name)
        if func_data is None:
            return default
        if isinstance(func_data, ToolData):
            return func_data.func
        return default

    def get_tools(self) -> dict[str, ToolData]:
        return {
            name: data
            for name, data in self._models.items()
            if (name not in self._disabled_tools and data.enable_if())
        }

    def tools_meta(self) -> dict[str, ToolFunctionSchema]:
        return {
            k: v.data
            for k, v in self._models.items()
            if (k not in self._disabled_tools and v.enable_if())
        }

    def tools_meta_dict(self, **kwargs) -> dict[str, dict[str, Any]]:
        return {
            k: v.data.model_dump(**kwargs)
            for k, v in self._models.items()
            if (k not in self._disabled_tools and v.enable_if())
        }

    def register_tool(self, tool: ToolData) -> None:
        if tool.data.function.name not in self._models:
            self._models[tool.data.function.name] = tool
        else:
            raise ValueError(f"Tool {tool.data.function.name} already exists")

    def remove_tool(self, name: str) -> None:
        self._models.pop(name, None)
        if name in self._disabled_tools:
            self._disabled_tools.remove(name)

    def enable_tool(self, name: str) -> None:
        if name in self._disabled_tools:
            self._disabled_tools.remove(name)
        else:
            raise ValueError(f"Tool {name} is not disabled")

    def disable_tool(self, name: str) -> None:
        if self.has_tool(name):
            self._disabled_tools.add(name)
        else:
            raise ValueError(f"Tool {name} does not exist or has been disabled")

    def get_disabled_tools(self) -> list[str]:
        return list(self._disabled_tools)


class ToolsManager(MultiToolsManager):
    _instance = None
    _initialized = False

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self.__class__._initialized:
            super().__init__()
            self.__class__._initialized = True


def _parse_google_docstring(docstring: str | None) -> tuple[str, dict[str, str]]:
    """
    Parse Google-style docstring to extract function description and parameter descriptions.Yes, just like this function's doc.

    Args:
        docstring: The docstring to parse

    Returns:
        A tuple containing (function_description, parameter_descriptions_dict)
    """
    if not docstring:
        return "(no description provided for this tool)", {}

    lines = [line.strip() for line in docstring.split("\n") if line.strip()]
    args_start_idx = -1
    for i, line in enumerate(lines):
        if line.lower().startswith("args:") or line.lower().startswith("参数:"):
            args_start_idx = i
            break
    if args_start_idx != -1:
        func_desc_lines: list[str] = lines[:args_start_idx]
        func_desc: str = " ".join(func_desc_lines).strip()
        args_lines: list[str] = lines[args_start_idx + 1 :]
    else:
        func_desc = " ".join(lines).strip()
        args_lines = []

    param_descriptions = {}
    param_pattern = r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\(([^)]+)\))?\s*:\s*(.*)"

    for line in args_lines:
        match = re.match(param_pattern, line)
        if match:
            param_name = match.group(1)
            param_desc = match.group(3).strip()

            if param_desc:
                param_descriptions[param_name] = param_desc
            else:
                param_descriptions[param_name] = f"Parameter {param_name}"

    if not func_desc:
        func_desc = "(no description provided for this tool)"

    return func_desc, param_descriptions


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


def _convert_pydantic_model_to_property_schema(
    model_class: type[BaseModel], globalns: dict[str, Any]
) -> FunctionPropertySchema:
    """Convert a Pydantic model to FunctionPropertySchema recursively"""
    if not _is_pydantic_model(model_class):
        raise ValueError(f"Expected Pydantic BaseModel, got {model_class.__name__}")

    # Get field definitions from the model
    properties = {}
    required_fields = []

    for field_name, field_info in model_class.__pydantic_fields__.items():
        field_type = field_info.annotation
        field_desc = field_info.description or f"Field {field_name}"

        # Check for Any or object types
        if field_type is Any or field_type is object:
            raise ValueError(
                f"Field '{field_name}' in Pydantic model '{model_class.__name__}' uses Any or object type, which is not allowed"
            )

        # Convert field type to FunctionPropertySchema
        field_schema = _python_type_to_property_schema(field_type, globalns, field_desc)
        properties[field_name] = field_schema

        # Check if field is required
        if field_info.is_required():
            required_fields.append(field_name)

    return FunctionPropertySchema(
        type="object",
        description=f"Pydantic model {model_class.__name__}",
        properties=properties,
        required=required_fields,
    )


def _python_type_to_property_schema(
    python_type: Any, globalns: dict[str, Any], description: str = "No description"
) -> FunctionPropertySchema:
    """Convert Python type to FunctionPropertySchema with full JSON Schema support"""
    # Handle basic types
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

    # Handle Pydantic models
    if _is_pydantic_model(python_type):
        return _convert_pydantic_model_to_property_schema(python_type, globalns)

    # Handle generic types (List, Dict, Union, etc.)
    origin = get_origin(python_type) if python_type not in (list, dict) else python_type

    # Handle bare types like 'list' and 'dict'
    if python_type is list or python_type is dict:
        if python_type is list:
            raise ValueError("List type must have a specified element type")
        elif python_type is dict:
            raise ValueError("Dict type must have a specified element type")

    if origin is not None:
        args = get_args(python_type)

        if origin is list:
            if not args:
                raise ValueError("List type must have a specified element type")
            item_type = args[0]
            if item_type is Any or item_type is object:
                raise ValueError("List elements cannot be Any or object type")

            # Check if item_type is itself a container (nested containers not allowed)
            if _is_container_type(item_type):
                raise ValueError(
                    "Nested containers are not allowed. Use Pydantic models for complex nested structures."
                )

            # Recursively convert the item type
            item_schema = _python_type_to_property_schema(
                item_type, globalns, "List item"
            )
            return FunctionPropertySchema(
                type="array", description=description, items=item_schema
            )

        elif origin is dict:
            # Dict types are not supported in tool parameters
            # Users should use Pydantic models instead for object structures
            raise ValueError(
                "Dict types are not supported in tool parameters. Use Pydantic models to define object structures."
            )

        elif origin is typing.Union or origin is types.UnionType:
            # Handle both typing.Union and Python 3.10+ UnionType (str | int)
            # For both cases, get_args returns the type arguments
            args = get_args(python_type)
            non_none_types = [arg for arg in args if arg is not type(None)]

            if len(non_none_types) == 1:
                # This is Optional[T]
                main_type = non_none_types[0]
                if main_type is Any or main_type is object:
                    raise ValueError("Optional type cannot contain Any or object")
                schema = _python_type_to_property_schema(
                    main_type, globalns, description
                )
                # For Optional, we don't set nullable in JSON Schema
                # The caller should handle required vs optional at the parameter level
                return schema
            else:
                # Reject Union of multiple types (non-Optional unions)
                raise ValueError(
                    f"Union types with multiple non-None types are not supported: {python_type}"
                )

    # Handle other types by falling back to string
    return FunctionPropertySchema(type="string", description=description)


def simple_tool(func: Callable[..., Any | Awaitable[Any]]):
    """
    A decorator that creates a ToolData object based on the function signature and annotations.
    It automatically generates parameter descriptions and metadata.

    Supported Types:
    - Basic types: str, int, float, bool
    - Pydantic BaseModel classes (for complex object structures)
    - List[T] where T is a supported type (single-level containers only)
    - Optional[T] (equivalent to Union[T, None])

    Unsupported Types (will raise ValueError):
    - Dict types (use Pydantic models instead for object structures)
    - Nested containers (e.g., List[List[str]], Dict[str, List[int]])
    - Union types with multiple non-None types (e.g., Union[str, int])
    - Any or object types
    - Custom types not covered above

    Example:

        ```python
        @simple_tool
        def add(a: int, b: int) -> int:
            \"""Add two numbers together.

            Args:
                a (int): The first number.
                b (int): The second number.

            Returns:
                int: The sum of the two numbers.
            \"""
            return a + b
        ```
    """
    signature: inspect.Signature = inspect.signature(func)
    func_desc, param_descriptions = _parse_google_docstring(func.__doc__)
    # Use globals() as the namespace for type resolution
    globalns: dict[str, Any] = getattr(func, "__globals__", globals())
    type_hints: dict[str, Any] = get_type_hints(func, globalns=globalns, localns={})
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in signature.parameters.items():
        if param_name == "self":
            continue
        param_type = type_hints.get(param_name)
        param_desc = param_descriptions.get(param_name, f"Parameter {param_name}")

        if param_type:
            # Check for Any or object types at the top level
            if param_type is Any or param_type is object:
                raise ValueError(
                    f"Parameter '{param_name}' uses '{param_type.__name__}' type, which is not allowed"
                )
            property_schema = _python_type_to_property_schema(
                param_type, globalns, param_desc
            )
        else:
            raise TypeError(
                f"Parameter '{param_name}' in {func.__name__} must have a type hint"
            )

        is_required = param.default == inspect.Parameter.empty
        if is_required:
            required.append(param_name)

        properties[param_name] = property_schema

    parameters_schema = FunctionParametersSchema(
        type="object", properties=properties, required=required
    )

    function_def = FunctionDefinitionSchema(
        name=func.__name__, description=func_desc, parameters=parameters_schema
    )

    @on_tools(function_def, strict=True)
    @wraps(func)
    async def tool_wrapper(params: dict[str, Any]) -> str:
        bound_args: inspect.BoundArguments = signature.bind(**params)
        bound_args.apply_defaults()

        result = (
            await func(**bound_args.arguments)
            if iscoroutinefunction(func)
            else await asyncio.to_thread(func, **bound_args.arguments)
        )

        # Convert result to string as expected by the schema
        return (
            json.dumps(result, indent=4, ensure_ascii=False)
            if isinstance(
                result,
                (
                    list,
                    dict,
                ),
            )
            else str(result)
        )

    return tool_wrapper


def on_tools(
    data: FunctionDefinitionSchema,
    custom_run: bool = False,
    strict: bool = False,
    enable_if: Callable[[], bool] = lambda: True,
) -> Callable[
    ...,
    Callable[[dict[str, Any]], Awaitable[str]]
    | Callable[[ToolContext], Awaitable[str | None]],
]:
    """Tool registration decorator

    Args:
        data (FunctionDefinitionSchema): Function metadata
        custom_run (bool, optional): Whether to enable custom run mode. Defaults to False.
        strict (bool, optional): Whether to enable strict mode. Defaults to False.
        show_call (bool, optional): Whether to show tool call. Defaults to True.
    """

    def decorator(
        func: Callable[[dict[str, Any]], Awaitable[str]]
        | Callable[[ToolContext], Awaitable[str | None]],
    ):
        tool_data = ToolData(
            func=func,
            data=ToolFunctionSchema(function=data, type="function", strict=strict),
            custom_run=custom_run,
            enable_if=enable_if,
        )
        ToolsManager().register_tool(tool_data)
        return func

    return decorator
