"""TypedDict subclasses for builtin metadata payloads."""

from __future__ import annotations

from amrita_core.contents import MessageMetadataPayload


class AgentReasoningMetadata(MessageMetadataPayload):
    """Metadata for pre-resolve reasoning summary."""

    last_step: str
    summary: str


class AgentReasoningChunkMetadata(MessageMetadataPayload):
    """Metadata for streaming reasoning chunks."""

    content: str


class AgentToolCallMetadata(MessageMetadataPayload):
    """Metadata for tool call notifications."""

    function_name: str
    is_done: bool
    tool_id: str
    err: BaseException | None


class AgentLoopErrorMetadata(MessageMetadataPayload):
    """Metadata for loop reasoning detection errors."""

    chat_object_id: str
    error: str


class AgentMiddleMessageMetadata(MessageMetadataPayload):
    """Metadata for LLM middle messages."""

    content: str


class HookErrorMetadata(MessageMetadataPayload):
    """Metadata for hook-level error responses (e.g. cookie filter)."""

    content: str
