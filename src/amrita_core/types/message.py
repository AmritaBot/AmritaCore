from __future__ import annotations

import typing
from collections.abc import Iterable
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Generic, Literal

from pydantic import ConfigDict, Field, model_validator
from typing_extensions import Self

from amrita_core.types.base import BaseModel
from amrita_core.types.content import CT_MAP, USER_INPUT
from amrita_core.types.tool import ToolCall, ToolResult

if TYPE_CHECKING:
    from amrita_core.types.memory import MemoryModel

_T = typing.TypeVar("_T", bound=USER_INPUT)


class Message(BaseModel, Generic[_T]):
    model_config = ConfigDict(extra="allow")
    role: Literal["user", "assistant", "system"] = Field(..., description="Role")
    content: _T = Field(..., description="Content")
    tool_calls: list[ToolCall] | None = Field(
        default=None, description="Tool calls", exclude_if=lambda x: x is None
    )
    reasoning_content: str | None = Field(
        default=None,
        description="Reasoning/thinking content from model",
        exclude_if=lambda x: x is None,
    )
    reasoning_signature: str | None = Field(
        default=None,
        description="Anthropic thinking signature (required for round-tripping)",
        exclude_if=lambda x: x is None,
    )

    @model_validator(mode="before")
    @classmethod
    def validate_content(cls, data: Any) -> Any:
        """Validate and properly deserialize content based on its structure."""
        if isinstance(data, dict) and "content" in data:
            content = data["content"]
            if isinstance(content, list):
                validated_content = []
                for item in content:
                    if isinstance(item, dict):
                        if "type" not in item:
                            raise ValueError("Content item is missing 'type' field")
                        content_type = item["type"]
                        if content_type in CT_MAP:
                            validated_item = CT_MAP[content_type].model_validate(item)
                            validated_content.append(validated_item)
                        else:
                            raise ValueError(
                                f"Unknown content type: `{content_type}`, please register it by calling `register_content` first."
                            )
                    else:
                        validated_content.append(item)
                data["content"] = validated_content
        return data

    @model_validator(mode="after")
    def validate_reasoning_content(self) -> Self:
        """Ensure reasoning_content is only present on assistant messages."""
        if self.role != "assistant" and self.reasoning_content is not None:
            raise ValueError(
                f"reasoning_content is only allowed on assistant messages, "
                f"got role={self.role!r}"
            )
        return self


CONTENT_LIST_TYPE_ITEM = Message | ToolResult
CONTENT_LIST_TYPE = list[CONTENT_LIST_TYPE_ITEM]


class SendMessageWrap(Iterable[CONTENT_LIST_TYPE_ITEM]):
    """Wrapper class for CONTENT_LIST_TYPE"""

    train: Message[str]  # system message
    memory: CONTENT_LIST_TYPE  # Messages without system message
    user_query: Message
    end_messages: CONTENT_LIST_TYPE  # End messages

    def __init__(
        self,
        train: dict[str, str] | Message[str],
        memory: CONTENT_LIST_TYPE | MemoryModel,
        user_query: Message | None = None,
    ):
        self.train = (
            train if isinstance(train, Message) else Message.model_validate(train)
        )
        self.end_messages = []
        self.memory = memory if isinstance(memory, list) else memory.messages
        query = user_query or self.memory[-1]
        if isinstance(query, ToolResult) or query.role != "user":
            raise ValueError("Invalid query message, expecting user message!")
        self.user_query = query
        if not user_query:
            self.memory.pop()

    @classmethod
    def validate_messages(cls, messages: CONTENT_LIST_TYPE) -> SendMessageWrap:
        train = messages[0]
        if train.role != "system":  # Fall back to match the first system message
            for idx, msg in enumerate(messages):
                if msg.role == "system":
                    train = msg
                    messages.pop(idx)
                    memory = messages
                    break
            else:
                raise ValueError("Invalid messages, expecting system message!")
        else:
            memory = messages[1:]
        return cls(
            train,
            memory,
        )

    def __len__(self) -> int:
        return len(self.memory) + 2 + len(self.end_messages)

    def __iter__(self) -> typing.Iterator[CONTENT_LIST_TYPE_ITEM]:
        yield self.train
        yield from self.memory
        yield self.user_query
        yield from self.end_messages

    def copy(self) -> SendMessageWrap:
        return deepcopy(self)

    def unwrap(self, exclude_system: bool = False) -> CONTENT_LIST_TYPE:
        system_msg: CONTENT_LIST_TYPE = [self.train] if not exclude_system else []
        return [*system_msg, *self.memory, self.user_query, *self.end_messages]

    def get_train(self) -> Message[str]:
        return self.train

    def get_memory(self) -> CONTENT_LIST_TYPE:
        return self.memory

    def get_user_query(self) -> Message:
        return self.user_query

    def append(self, message: CONTENT_LIST_TYPE_ITEM) -> None:
        self.end_messages.append(message)

    def extend(self, messages: CONTENT_LIST_TYPE) -> None:
        self.end_messages.extend(messages)
