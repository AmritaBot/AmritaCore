from __future__ import annotations

import typing
from typing import Generic, Literal
from uuid import uuid4

from pydantic import ConfigDict, Field

from amrita_core.types.base import BaseModel
from amrita_core.types.tool import ToolCall

T = typing.TypeVar("T", str, None, typing.Literal[""] | None)
T_INT = typing.TypeVar("T_INT", int, None, int | None)
T_TOOL = typing.TypeVar("T_TOOL", list[ToolCall], None, list[ToolCall] | None)
STOP_REASON = Literal[
    "end_turn",
    "max_tokens",
    "stop_sequence",
    "tool_use",
    "pause_turn",
    "refusal",
]


class UniResponseUsage(BaseModel, Generic[T_INT]):
    prompt_tokens: T_INT
    """The number of prompt tokens which were used."""
    completion_tokens: T_INT
    """The number of completion tokens which were used."""
    total_tokens: T_INT
    """The total number of tokens which were used."""
    cache_creation: int | None = None
    """The number of tokens used to create the cache entry."""
    cache_hit: int | None = None
    """The number of tokens read from the cache."""

    model_config = ConfigDict(extra="allow")


class RequestMetadata(BaseModel):
    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique request ID",
    )
    original_request_id: str | None = Field(
        default=None,
        description="Original request ID from Adapter",
    )
    model: str = Field(default="__NOT_GIVEN__", description="LLM Used for request")
    stop_sequence: str | None = Field(
        default=None,
        description="Stop sequence",
    )
    stop_reason: STOP_REASON | None = Field(
        default=None,
        description="Stop reason",
    )
    model_config = ConfigDict(extra="allow")


class UniResponse(
    BaseModel,
    Generic[T, T_TOOL],
):
    """Unified response format"""

    model_config = ConfigDict(extra="allow")

    role: Literal["assistant"] = Field(
        default="assistant",  # Regardless of whether there's content/tool_call, role is assistant
        description="Role",
    )

    usage: UniResponseUsage | None = None
    content: T = Field(
        ...,
        description="Content",
        exclude_if=lambda x: x is None,
    )
    tool_calls: T_TOOL = Field(
        ...,
        description="Tool call results",
        exclude_if=lambda x: x is None,
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
    metadata: RequestMetadata = Field(
        default_factory=RequestMetadata,
        description="Request metadata",
    )
