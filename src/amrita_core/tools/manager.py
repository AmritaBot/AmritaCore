import inspect
import re
import typing
from asyncio import iscoroutinefunction
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, get_args, get_origin, get_type_hints, overload

from typing_extensions import Self

from .models import (
    JSON_OBJECT_TYPE,
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
    ToolContext,
    ToolData,
    ToolFunctionSchema,
)

T = typing.TypeVar("T")


class MultiToolsManager:
    _models: dict[str, ToolData]
    _disabled_tools: set[
        str
    ]  # Disabled tools, has_tool and get_tool will not return disabled tools

    def __init__(self):
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


def simple_tool(func: Callable[..., Any | Awaitable[Any]]):
    """
    A decorator that creates a ToolData object based on the function signature and annotations.
    It automatically generates parameter descriptions and metadata.

    Here is an example of how to use this decorator:

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
    type_hints: dict[str, Any] = get_type_hints(
        func, globalns=globals(), localns=locals()
    )
    properties = {}
    required = []

    for param_name, param in signature.parameters.items():
        if param_name == "self":
            continue
        param_type = type_hints.get(param_name)
        json_type: JSON_OBJECT_TYPE = "string"
        if param_type:
            if hasattr(param_type, "__origin__"):
                origin = get_origin(param_type)
                if origin is not None:
                    if issubclass(origin, list):
                        json_type = "array"
                    elif issubclass(origin, dict):
                        json_type = "object"
                    elif origin is typing.Union:
                        args = get_args(param_type)
                        if type(None) in args:
                            pass
                        else:
                            non_none_types = [
                                arg for arg in args if arg is not type(None)
                            ]
                            if non_none_types:
                                param_type = non_none_types[0]
                                json_type = _python_type_to_json_type(param_type)
                else:
                    json_type = _python_type_to_json_type(param_type)
            else:
                json_type = _python_type_to_json_type(param_type)
        param_desc = param_descriptions.get(param_name, f"Parameter {param_name}")
        is_required = param.default == inspect.Parameter.empty
        if is_required:
            required.append(param_name)
        property_schema = FunctionPropertySchema(type=json_type, description=param_desc)

        properties[param_name] = property_schema

    parameters_schema = FunctionParametersSchema(
        type="object", properties=properties if properties else None, required=required
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
            else func(**bound_args.arguments)
        )

        # Convert result to string as expected by the schema
        return str(result)

    return tool_wrapper


def _python_type_to_json_type(python_type: type[Any]) -> JSON_OBJECT_TYPE:
    """Convert Python type to JSON schema type."""
    if python_type is str:
        return "string"
    elif python_type is int:
        return "integer"
    elif python_type is float:
        return "number"
    elif python_type is bool:
        return "boolean"
    elif python_type is list:
        return "array"
    elif python_type is dict:
        return "object"
    else:
        return "string"


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
