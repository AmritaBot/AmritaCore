from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from amrita_core.chatmanager import ChatObject
from amrita_core.types import CONTENT_LIST_TYPE, USER_INPUT, SendMessageWrap


class EventTypeEnum(str, Enum):
    """
    EventTypeEnum class is used to define and manage different event types.
    It encapsulates the string identifiers of event types, providing a structured way
    to handle and retrieve event types.

    """

    COMPLETION = "COMPLETION"
    Nil = "Nil"
    BEFORE_COMPLETION = "BEFORE_COMPLETION"

    def validate(self, name: str) -> bool:
        return name in self


@dataclass
class Event:
    user_input: USER_INPUT
    original_context: CONTENT_LIST_TYPE
    chat_object: ChatObject

    def __post_init__(self):
        # Initialize event type as none
        self._event_type = EventTypeEnum.Nil
        # Validate and store messages using SendMessageWrap
        self._context_messages: SendMessageWrap = SendMessageWrap.validate_messages(
            self.original_context
        )

    @property
    def event_type(self) -> EventTypeEnum:
        return self._event_type

    @property
    def message(self) -> SendMessageWrap:
        return self._context_messages

    def get_context_messages(self) -> SendMessageWrap:
        return self._context_messages

    def get_event_type(self) -> str:
        raise NotImplementedError

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
    def event_type(self):
        return EventTypeEnum.COMPLETION

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
    def event_type(self) -> EventTypeEnum:
        return self._event_type

    def get_event_type(self) -> str:
        return self._event_type
