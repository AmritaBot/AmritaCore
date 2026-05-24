import warnings

from amrita_sense.weakcache import WeakValueLRUCache

warnings.warn(
    "amrita_core.weakcache is deprecated and will be removed in a future release. Please use amrita_sense.weakcache instead.",
    DeprecationWarning,
    stacklevel=2,
)
__all__ = ["WeakValueLRUCache"]
