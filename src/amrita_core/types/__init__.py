from __future__ import annotations

from amrita_core.types.base import BaseModel, DirtyAwareBaseModel
from amrita_core.types.content import (
    CT_MAP,
    USER_INPUT,
    Content,
    File,
    FileContent,
    ImageContent,
    ImageUrl,
    TextContent,
    register_content,
)
from amrita_core.types.embedding import EmbeddingChunk
from amrita_core.types.memory import MemoryModel
from amrita_core.types.message import (
    CONTENT_LIST_TYPE,
    CONTENT_LIST_TYPE_ITEM,
    Message,
    SendMessageWrap,
)
from amrita_core.types.preset import ModelConfig, ModelPreset, ThinkingConfig
from amrita_core.types.response import UniResponse, UniResponseUsage
from amrita_core.types.tool import Function, ToolCall, ToolResult

# Register built-in content types
register_content(TextContent)
register_content(ImageContent)
register_content(FileContent)

__all__ = [
    "CONTENT_LIST_TYPE",
    "CONTENT_LIST_TYPE_ITEM",
    "CT_MAP",
    "USER_INPUT",
    "BaseModel",
    "Content",
    "DirtyAwareBaseModel",
    "EmbeddingChunk",
    "File",
    "FileContent",
    "Function",
    "ImageContent",
    "ImageUrl",
    "MemoryModel",
    "Message",
    "ModelConfig",
    "ModelPreset",
    "SendMessageWrap",
    "TextContent",
    "ThinkingConfig",
    "ToolCall",
    "ToolResult",
    "UniResponse",
    "UniResponseUsage",
    "register_content",
]
