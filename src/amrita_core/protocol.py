from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Iterable
from dataclasses import dataclass, field
from typing import Any

from amrita_core.config import AmritaConfig, get_config

from .logging import logger
from .tools.models import ToolChoice, ToolFunctionSchema
from .types import ModelPreset, ToolCall, UniResponse


class ResponseWrapper(
    ABC
):  # It will be used in next generation (planned on AmritaCore 1.x)
    """Base class for response wrapper"""

    @abstractmethod
    def __str__(self) -> str:
        """Get response content"""

    @abstractmethod
    def get_type(self) -> str:
        """Get the type of the response"""

    @abstractmethod
    def get_content(self) -> Any:
        """Get the content of the response"""


@dataclass
class ModelAdapter:
    """Base class for model adapter"""

    preset: ModelPreset
    config: AmritaConfig = field(default_factory=get_config)
    __override__: bool = False  # Whether to allow overriding existing adapters

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if not getattr(cls, "__abstract__", False):
            AdapterManager().register_adapter(cls)

    @abstractmethod
    async def call_api(
        self, messages: Iterable
    ) -> AsyncGenerator[str | UniResponse[str, None], None]:
        yield ""

    async def call_tools(
        self,
        messages: Iterable,
        tools: list[ToolFunctionSchema],
        tool_choice: ToolChoice | None = None,
    ) -> UniResponse[None, list[ToolCall] | None]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_adapter_protocol() -> str | tuple[str, ...]: ...

    @property
    def protocol(self):
        """Get model protocol adapter"""
        return self.get_adapter_protocol()


class AdapterManager:
    __instance = None
    _adapter_class: dict[str, type[ModelAdapter]]

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance._adapter_class = {}
        return cls.__instance

    def get_adapters(self) -> dict[str, type[ModelAdapter]]:
        """Get all registered adapters"""
        return self._adapter_class

    def safe_get_adapter(self, protocol: str) -> type[ModelAdapter] | None:
        """Get adapter"""
        return self._adapter_class.get(protocol)

    def get_adapter(self, protocol: str) -> type[ModelAdapter]:
        """Get adapter"""
        if protocol not in self._adapter_class:
            raise ValueError(f"No adapter found for protocol {protocol}")
        return self._adapter_class[protocol]

    def register_adapter(self, adapter: type[ModelAdapter]):
        """Register adapter"""
        protocol = adapter.get_adapter_protocol()
        override = adapter.__override__ if hasattr(adapter, "__override__") else False
        if isinstance(protocol, str):
            if protocol in self._adapter_class:
                if not override:
                    raise ValueError(
                        f"Model protocol adapter {protocol} is already registered"
                    )
                logger.warning(
                    f"Model protocol adapter {protocol} has been registered by {self._adapter_class[protocol].__name__}, overriding existing adapter"
                )

            self._adapter_class[protocol] = adapter
        elif isinstance(protocol, tuple):
            for p in protocol:
                if not isinstance(p, str):
                    raise TypeError(
                        "Model protocol adapter must be a string or tuple of strings"
                    )
                if p in self._adapter_class:
                    if not override:
                        raise ValueError(
                            f"Model protocol adapter {p} is already registered"
                        )
                    logger.warning(
                        f"Model protocol adapter {p} has been registered by {self._adapter_class[p].__name__}, overriding existing adapter"
                    )
                self._adapter_class[p] = adapter
