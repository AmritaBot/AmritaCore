import warnings

from .base.adapter import (
    ADAPTER_TYPE,
    COMPLETION_RETURNING,
    AdapterManager,
    MessageContent,
    ModelAdapter,
)
from .contents import (
    ImageMessage,
    MessageMetadata,
    MessageWithMetadata,
    RawMessageContent,
    StringMessageContent,
    get_image_format,
)

warnings.warn(
    "amrita_core.protocol is deprecated and will be removed in a future release. Please use amrita_core.base.adapter and amrita_core.contents instead.Will be removed in v0.10.0",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "ADAPTER_TYPE",
    "COMPLETION_RETURNING",
    "AdapterManager",
    "ImageMessage",
    "MessageContent",
    "MessageMetadata",
    "MessageWithMetadata",
    "ModelAdapter",
    "RawMessageContent",
    "StringMessageContent",
    "get_image_format",
]
