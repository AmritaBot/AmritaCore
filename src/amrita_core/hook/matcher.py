import warnings

from amrita_sense.hook.matcher import EventRegistry, Matcher, MatcherFactory

warnings.warn(
    "amrita_core.hook.matcher is deprecated and will be removed in a future release. Please use amrita_sense.hook.matcher instead.Will be removed in v0.10.0",
    DeprecationWarning,
    stacklevel=2,
)
MatcherManager = MatcherFactory
__all__ = ["EventRegistry", "Matcher", "MatcherFactory", "MatcherManager"]
