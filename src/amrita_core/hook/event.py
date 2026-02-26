from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from typing_extensions import Never, override

from amrita_core.hook.exception import FallbackFailed
from amrita_core.types import USER_INPUT, ModelPreset, SendMessageWrap

if TYPE_CHECKING:
    from amrita_core.chatmanager import ChatObject
    from amrita_core.config import AmritaConfig


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
class BaseEvent(ABC):
    """All events must inherit from this class"""

    @abstractmethod
    def get_event_type(self) -> EventTypeEnum | str:
        raise NotImplementedError

    @property
    @abstractmethod
    def event_type(self) -> EventTypeEnum | str: ...


@dataclass
class FallbackContext(BaseEvent):
    preset: ModelPreset
    exc_info: BaseException
    config: "AmritaConfig"
    context: SendMessageWrap
    term: int

    def __post_init__(self):
        self._event_type = EventTypeEnum.PRESET_FALLBACK

    @property
    def event_type(self) -> EventTypeEnum:
        return self._event_type

    def get_event_type(self) -> EventTypeEnum:
        return self._event_type

    def fail(self, reason: Any | None = None) -> Never:
        """Mark the event as failed"""
        raise FallbackFailed(reason)


@dataclass
class Event(BaseEvent):
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
    def get_event_type(self) -> str:
        return EventTypeEnum.COMPLETION

    def get_model_response(self) -> str:
        return self.model_response


@dataclass
class PreCompletionEvent(Event):
    def __post_init__(self):
        super().__post_init__()
        self._event_type = EventTypeEnum.BEFORE_COMPLETION

    @property
    @override
    def event_type(self) -> EventTypeEnum:
        return self._event_type

    @override
    def get_event_type(self) -> str:
        return self._event_type
