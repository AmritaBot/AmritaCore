import warnings

from amrita_core.enums import BuiltinName, SuspendEnum

warnings.warn(
    "This module is deprecated and will be removed in a future release (0.13.x). Please use amrita_core.enums instead.",
    DeprecationWarning,
)

__all__ = [
    "BuiltinName",
    "SuspendEnum",
]
