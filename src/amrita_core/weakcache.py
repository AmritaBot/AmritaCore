import warnings

from amrita_sense.weakcache import WeakValueLRUCache

warnings.warn(
    "amrita_core.weakcache is deprecated and will be removed in a future release. Please use amrita_sense.weakcache instead.Will be removed in v0.10.0",
    DeprecationWarning,
    stacklevel=2,
)
__all__ = ["WeakValueLRUCache"]
