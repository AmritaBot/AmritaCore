from __future__ import annotations

import typing
from typing import Generic, Literal

from pydantic import ConfigDict, Field

from amrita_core.types.base import BaseModel
from amrita_core.types.tool import ToolCall

T = typing.TypeVar("T", None, str, None | typing.Literal[""])
T_INT = typing.TypeVar("T_INT", int, None, int | None)
T_TOOL = typing.TypeVar("T_TOOL", list[ToolCall], None, list[ToolCall] | None)


class UniResponseUsage(BaseModel, Generic[T_INT]):
    prompt_tokens: T_INT
    completion_tokens: T_INT
    total_tokens: T_INT


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
