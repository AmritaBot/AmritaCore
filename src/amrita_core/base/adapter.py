from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Iterable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from amrita_core.config import AmritaConfig, get_config
from amrita_core.threadsafe import ContextThreadsafe

from ..logging import logger
from ..tools.models import ToolChoice, ToolFunctionSchema
from ..types import EmbeddingChunk, ModelPreset, ToolCall, UniResponse


class MessageContent(ABC):
    """Abstract base class for different types of message content

    This allows for various types of content to be yielded by the chat manager,
    not just strings. Subclasses should implement their own representation.
    """

    def __str__(self) -> str:
        return self.get_content()

    def __init__(self, content_type: str):
        self.type = content_type

    @abstractmethod
    def get_content(self):
        """Return the actual content of the message"""
        raise NotImplementedError("Subclasses must implement get_content method")


COMPLETION_RETURNING = MessageContent | str | UniResponse[str, None]
ADAPTER_TYPE = Literal[
    "text-gen",
    "embed",
    # "rerank",
]


@dataclass
class ModelAdapter:
    """Base class for model adapter"""

    preset: ModelPreset
    config: AmritaConfig = field(default_factory=get_config)
    __override__: bool = False  # Whether to allow overriding existing adapters

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if not getattr(cls, "__abstract__", False) and not getattr(
            cls, "__no_register__", False
        ):
            AdapterManager().register_adapter(cls)

    async def call_api(
        self, messages: Iterable, **kwargs
    ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
        if TYPE_CHECKING:
            yield ""
        else:
            raise NotImplementedError

    async def call_tools(
        self,
        messages: Iterable,
        tools: list[ToolFunctionSchema],
        tool_choice: ToolChoice | None = None,
    ) -> UniResponse[None, list[ToolCall] | None]:
        raise NotImplementedError

    async def call_embed(
        self, texts: Sequence[str], **kwargs
    ) -> Sequence[EmbeddingChunk]:
        raise NotImplementedError

    # TODO: Add reranker support.

    @staticmethod
    @abstractmethod
    def get_adapter_protocol() -> str | tuple[str, ...]: ...

    @staticmethod
    def get_type() -> ADAPTER_TYPE | tuple[ADAPTER_TYPE, ...]:
        return "text-gen"

    @property
    def protocol(self):
        """Get model protocol adapter"""
        return self.get_adapter_protocol()


class AdapterManager(ContextThreadsafe):
    __instance = None
    __inited = False
    _adapter_class: dict[str, type[ModelAdapter]]

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance._adapter_class = {}
        return cls.__instance

    def __init__(self):
        if not self.__inited:
            super().__init__()
            self.__inited = True

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


__all__ = [
    "ADAPTER_TYPE",
    "COMPLETION_RETURNING",
    "AdapterManager",
    "MessageContent",
    "ModelAdapter",
]
