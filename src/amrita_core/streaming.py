import warnings

from amrita_sense.streaming import SUSPEND_ON_YIELD, ObjectTypeT, SuspendObjectStream

warnings.warn(
    "amrita_core.streaming is deprecated and will be removed in a future release. Please use amrita_sense.streaming instead.",
    DeprecationWarning,
    stacklevel=2,
)
__all__ = ["SUSPEND_ON_YIELD", "ObjectTypeT", "SuspendObjectStream"]
