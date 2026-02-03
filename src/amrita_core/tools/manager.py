import typing
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, overload

from typing_extensions import Self

from .models import FunctionDefinitionSchema, ToolContext, ToolData, ToolFunctionSchema

T = typing.TypeVar("T")


class ToolsManager:
    _instance = None
    _models: ClassVar[dict[str, ToolData]] = {}
    _disabled_tools: ClassVar[set[str]] = (
        set()
    )  # Disabled tools, has_tool and get_tool will not return disabled tools

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

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
