from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Iterable, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, ClassVar, Literal

from amrita_sense.logging import logger

from amrita_core.config import AmritaConfig, get_config
from amrita_core.utils import _did_you_mean_hint

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
# agentic_call_api additionally carries the round's tool calls, so its trailing UniResponse is typed wider than call_api's.
AGENTIC_RETURNING = COMPLETION_RETURNING | UniResponse[str, list[ToolCall] | None]
ADAPTER_TYPE = Literal[
    "text-gen",
    "embed",
    # "rerank",
]


@dataclass(frozen=True, slots=True)
class FeatureFlag:
    """适配器出口能力的静态声明。

    读点集中在网关层：网关是所有适配器的直接消费者，由它决定这一轮请求的载荷能
    不能原样发出去。框架层（策略、上下文、存储）不读这些标记——它只处理标准数据
    模型，不该知道哪家协议支持什么。

    语义是 **wire 级别**的：字段描述的是「这类内容能否出现在发给该协议的请求里」，
    而不是「该模型能否理解这类内容」。后者无法可靠判定，前者可以。
    """

    agentic_call: bool = field(default=False)
    """是否实现 ``agentic_call_api``（同一请求里流式产出文本与工具调用）。"""

    input_multimodal: bool = field(default=False)
    """非文本块能否出现在 ``user`` / ``system`` 消息的内容里。"""

    tool_result_multimodal: bool = field(default=False)
    """非文本块能否出现在 ``tool`` 消息（工具返回值）的内容里。"""


_DEFAULT_FEATURES = FeatureFlag()


@dataclass
class ModelAdapter:
    """Base class for model adapter"""

    preset: ModelPreset
    config: AmritaConfig = field(default_factory=get_config)
    __override__: bool = False  # Whether to allow overriding existing adapters
    # 适配器出口能力声明。子类覆盖整个对象，而不是就地改字段——`FeatureFlag`
    # 是 frozen 的，改字段本身就不允许。
    features: ClassVar[FeatureFlag] = _DEFAULT_FEATURES
    # 兼容旧字段：子类若只声明了它，`__init_subclass__` 会搬进 `features`。
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
        """把旧式 ``supports_agentic_call`` 翻译进 :attr:`features`。

        第三方适配器只写了旧字段的情况必须继续生效，否则 ``agentic_call_api``
        会静默不再被调用，而症状只是一个「怎么没走流式」的疑问，极难定位。

        旧字段只描述流式这一种能力，所以它只能改这一个标记：在父类声明的副本上换掉
        ``agentic_call``，其余标记原样继承。整块新建一个默认对象的话，一个只想关掉
        流式的子类会顺手把父类的多模态声明一起清零，症状是「图怎么不发了」。
        """
        if "features" in cls.__dict__:
            # 显式声明了新标记，以它为准；旧字段跟着同步，外部读取方不会读到过期值
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
    ) -> UniResponse[None, list[ToolCall] | None]:
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
