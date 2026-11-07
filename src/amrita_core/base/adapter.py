from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Iterable, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, ClassVar, Literal

from amrita_sense.logging import logger

from amrita_core.config import AmritaConfig, get_config
from amrita_core.utils import _did_you_mean_hint

from ..tools.models import ToolChoice, ToolFunctionSchema
from ..types import EmbeddingChunk, ModelInfo, ModelPreset, ToolCall, UniResponse


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
# agentic_call_api additionally carries the round's tool calls, so its trailing UniResponse is typed wider than call_api's.
AGENTIC_RETURNING = COMPLETION_RETURNING | UniResponse[str, list[ToolCall] | None]
ADAPTER_TYPE = Literal[
    "text-gen",
    "embed",
    # "rerank",
]


@dataclass(frozen=True, slots=True)
class FeatureFlag:
    """Static declaration of an adapter's wire capabilities.

    Only the gateway reads these flags: it decides what this turn's payload can
    carry. Strategy, context and storage work on the framework's own models and
    never need to know which protocol supports what.

    The flags describe the wire, not the model: whether a block may appear in
    the request, not whether the model understands it. The latter cannot be
    decided reliably; the former can.
    """

    agentic_call: bool = field(default=False)
    """Whether ``agentic_call_api`` is implemented (text and tool calls from one request)."""

    input_multimodal: bool = field(default=False)
    """Whether non-text blocks may appear in ``user`` / ``system`` message content."""

    tool_result_multimodal: bool = field(default=False)
    """Whether non-text blocks may appear in ``tool`` message content (tool results)."""

    fetch_models: bool = field(default=False)
    """Whether ``fetch_models`` is implemented (lists the models a user may pick)."""


_DEFAULT_FEATURES = FeatureFlag()


@dataclass
class ModelAdapter:
    """Base class for model adapter"""

    preset: ModelPreset
    config: AmritaConfig = field(default_factory=get_config)
    __override__: bool = False  # Whether to allow overriding existing adapters
    # Adapter wire capabilities. Subclasses assign the whole object; FeatureFlag is frozen.
    features: ClassVar[FeatureFlag] = _DEFAULT_FEATURES
    # Legacy field: a subclass that only declares it gets folded into ``features``.
    supports_agentic_call: ClassVar[bool] = False

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls._sync_legacy_features()
        if not getattr(cls, "__abstract__", False) and not getattr(
            cls, "__no_register__", False
        ):
            AdapterManager().register_adapter(cls)

    @classmethod
    def _sync_legacy_features(cls) -> None:
        """Fold the legacy ``supports_agentic_call`` into :attr:`features`.

        Third-party adapters that only set the old field must keep working;
        otherwise ``agentic_call_api`` silently stops being called and the only
        symptom is a vague question about missing streaming.

        The old field describes streaming alone, so it may only change that one
        flag: copy the inherited declaration, swap ``agentic_call``, keep the
        rest. Building a fresh default object would also clear the parent's
        multimodal declarations, and the symptom would be images that suddenly
        stop being sent.
        """
        if "features" in cls.__dict__:
            # Explicit features win, and the legacy field is kept in sync for readers.
            cls.supports_agentic_call = cls.features.agentic_call
            return
        legacy = cls.__dict__.get("supports_agentic_call")
        if legacy is None:
            return
        inherited = cls.features
        if inherited.agentic_call == bool(legacy):
            return
        cls.features = replace(inherited, agentic_call=bool(legacy))

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
        **kwargs,
    ) -> UniResponse[str | None, list[ToolCall] | None]:
        raise NotImplementedError

    async def agentic_call_api(
        self,
        messages: Iterable,
        tools: list[ToolFunctionSchema] | None = None,
        tool_choice: ToolChoice | None = None,
        **kwargs,
    ) -> AsyncGenerator[AGENTIC_RETURNING, None]:
        """Stream text *and* tool calls from a single request.

        Optional capability: adapters that can drive an agent loop set
        :attr:`supports_agentic_call` and implement this. The default raises so
        callers fall back to the legacy ``call_api`` + ``call_tools`` path.
        """
        if TYPE_CHECKING:
            yield ""
        else:
            raise NotImplementedError

    @classmethod
    async def fetch_models(cls, preset: ModelPreset) -> list[ModelInfo]:
        """List the models this protocol exposes for ``preset``.

        Optional capability: adapters that can query a model catalogue set
        :attr:`FeatureFlag.fetch_models` and implement this. It is a class
        method because the call needs only the endpoint and credentials already
        on the preset - no configured instance, no conversation state.

        The default raises so callers can feature-detect instead of sending a
        request the provider may not support.
        """
        raise NotImplementedError(
            f"Adapter {cls.__name__} does not implement fetch_models"
        )

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


class AdapterManager:
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
            hint = _did_you_mean_hint(protocol, list(self._adapter_class.keys()))
            raise ValueError(f"No adapter found for protocol '{protocol}'.{hint}")
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
