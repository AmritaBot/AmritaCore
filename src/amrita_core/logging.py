import warnings

from amrita_sense.logging import (
    LoguruHandler,
    debug_log,
    default_filter,
    default_format,
    logger,
    logger_id,
)

warnings.warn(
    "amrita_core.logging is deprecated and will be removed in a future release. Please use amrita_sense.logging instead.Will be removed in v0.10.0",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "LoguruHandler",
    "debug_log",
    "default_filter",
    "default_format",
    "logger",
    "logger_id",
]
