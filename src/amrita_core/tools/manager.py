import asyncio
import inspect
import json
import re
import typing
from asyncio import iscoroutinefunction
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, overload

from typing_extensions import Self

from amrita_core.utils import _did_you_mean_hint

from .models import (
    FunctionDefinitionSchema,
    ToolContext,
    ToolData,
    ToolFunctionSchema,
)
from .schema import function_definition_from_signature

T = typing.TypeVar("T")
_ToolFunc = typing.TypeVar("_ToolFunc", bound=Callable[..., Awaitable[Any]])


class MultiToolsManager:
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
    ) -> ToolFunctionSchema | T | None:
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
        | T
        | None
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
            raise ValueError(f"Tool '{tool.data.function.name}' already exists.")

    def remove_tool(self, name: str) -> None:
        self._models.pop(name, None)
        if name in self._disabled_tools:
            self._disabled_tools.remove(name)

    def enable_tool(self, name: str) -> None:
        if name in self._disabled_tools:
            self._disabled_tools.remove(name)
        else:
            hint = _did_you_mean_hint(name, list(self._disabled_tools))
            raise ValueError(f"Tool '{name}' is not disabled.{hint}")

    def disable_tool(self, name: str) -> None:
        if self.has_tool(name):
            self._disabled_tools.add(name)
        else:
            hint = _did_you_mean_hint(name, list(self._models.keys()))
            raise ValueError(
                f"Tool '{name}' does not exist or has been disabled.{hint}"
            )

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


def simple_tool(
    func: Callable[..., Any | Awaitable[Any]],
) -> Callable[[dict[str, Any]], Awaitable[str]]:
    """
    A decorator that creates a ToolData object based on the function signature and annotations.
    It automatically generates parameter descriptions and metadata.

    Supported Types:
    - Basic types: str, int, float, bool
    - Pydantic BaseModel classes (for complex object structures), for this, please write a model with a description.
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
    function_def = function_definition_from_signature(
        func, description=func_desc, parameter_descriptions=param_descriptions
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
    bound_to: MultiToolsManager | None = None,
) -> Callable[[_ToolFunc], _ToolFunc]:
    """Tool registration decorator

    Args:
        data (FunctionDefinitionSchema): Function metadata
        custom_run (bool, optional): Whether to enable custom run mode. Defaults to False.
        strict (bool, optional): Whether to enable strict mode. Defaults to False.
        show_call (bool, optional): Whether to show tool call. Defaults to True.
        bound_to (MultiToolsManager | None, optional): Bound to tools manager. Defaults to None.
    """

    def decorator(func: _ToolFunc) -> _ToolFunc:
        tool_data = ToolData(
            func=func,
            data=ToolFunctionSchema(function=data, type="function", strict=strict),
            custom_run=custom_run,
            enable_if=enable_if,
        )
        tm = bound_to or ToolsManager()
        tm.register_tool(tool_data)
        return func

    return decorator
