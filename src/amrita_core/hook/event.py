from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from amrita_sense.hook.event import BaseEvent
from typing_extensions import Never, override

from amrita_core.hook.exception import FallbackFailed
from amrita_core.types import (
    CONTENT_LIST_TYPE,
    USER_INPUT,
    ModelPreset,
    SendMessageWrap,
)

if TYPE_CHECKING:
    from amrita_core.chatmanager import ChatObject
    from amrita_core.config import AmritaConfig
    from amrita_core.tools.models import ToolFunctionSchema


class EventTypeEnum(str, Enum):
    """
    EventTypeEnum class is used to define and manage different event types.
    It encapsulates the string identifiers of event types, providing a structured way
    to handle and retrieve event types.

    """

    COMPLETION = "COMPLETION"
    Nil = "Nil"
    BEFORE_COMPLETION = "BEFORE_COMPLETION"
    PRESET_FALLBACK = "PRESET_FALLBACK"

    @classmethod
    def validate(cls, name: str) -> bool:
        return name in cls.__members__


@dataclass
class FallbackContext(BaseEvent[EventTypeEnum]):
    """Base event for all preset-fallback events.

    Every fallback event shares the ``PRESET_FALLBACK`` event type; concrete
    subclasses distinguish the failing gateway call (completion / tools /
    embedding) so matchers can react differently to each kind.
    """

    preset: ModelPreset
    exc_info: BaseException
    config: "AmritaConfig"
    context: SendMessageWrap | CONTENT_LIST_TYPE | Sequence[str]
    term: int

    def __post_init__(self):
        self._event_type = EventTypeEnum.PRESET_FALLBACK

    @property
    def event_type(self) -> EventTypeEnum:
        return self._event_type

    def get_event_type(self) -> EventTypeEnum:
        return self._event_type

    def fail(self, reason: Any | None = None) -> Never:  # pragma: no cover
        """Mark the event as failed"""
        raise FallbackFailed(reason)


@dataclass
class CompletionFallbackContext(FallbackContext):
    """Fallback event fired when ``call_completion`` fails.

    ``context`` carries the validated message list (``CONTENT_LIST_TYPE``).
    """


@dataclass
class ToolsFallbackContext(FallbackContext):
    """Fallback event fired when ``tools_caller`` fails.

    ``context`` carries the validated message list (``CONTENT_LIST_TYPE``);
    ``tools`` carries the tool schemas of the failed call.
    """

    tools: list[ToolFunctionSchema] | None = None


@dataclass
class EmbeddingFallbackContext(FallbackContext):
    """Fallback event fired when ``call_embedding`` fails.

    ``context`` carries the input text sequence (``Sequence[str]``).
    """


@dataclass
class Event(BaseEvent[EventTypeEnum]):
    user_input: USER_INPUT
    original_context: SendMessageWrap
    chat_object: "ChatObject"

    def __post_init__(self):
        # Initialize event type as none
        self._event_type = EventTypeEnum.Nil
        # Validate and store messages using SendMessageWrap
        self._context_messages: SendMessageWrap = self.original_context

    @property
    def event_type(self) -> EventTypeEnum:

        return self._event_type

    @property
    def message(self) -> SendMessageWrap:
        return self._context_messages

    @message.setter
    def message(self, value: SendMessageWrap):
        if not isinstance(value, SendMessageWrap):
            raise TypeError("message must be of type SendMessageWrap")
        self._context_messages = value

    def get_context_messages(self) -> SendMessageWrap:
        return self._context_messages

    def get_user_input(self) -> USER_INPUT:
        return self.user_input


@dataclass
class CompletionEvent(Event):
    """Used after model completion"""

    model_response: str

    def __post_init__(self):
        super().__post_init__()
        # Initialize event type as completion event
        self._event_type = EventTypeEnum.COMPLETION

    @property
    @override
    def event_type(self):
        return EventTypeEnum.COMPLETION

    @override
    def get_event_type(self) -> EventTypeEnum:
        return EventTypeEnum.COMPLETION

    def get_model_response(self) -> str:
        return self.model_response


@dataclass
class PreCompletionEvent(Event):
    """Used before run strategy and completion"""

    def __post_init__(self):
        super().__post_init__()
        self._event_type = EventTypeEnum.BEFORE_COMPLETION

    @property
    @override
    def event_type(self) -> EventTypeEnum:
        return self._event_type

    @override
    def get_event_type(self) -> EventTypeEnum:
        return self._event_type


__all__ = [
    "BaseEvent",  # For backward compatibility
    "CompletionEvent",
    "CompletionFallbackContext",
    "EmbeddingFallbackContext",
    "Event",
    "EventTypeEnum",
    "FallbackContext",
    "PreCompletionEvent",
    "ToolsFallbackContext",
]
