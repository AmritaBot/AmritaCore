from amrita_sense.hook.exception import CancelException, MatcherException, PassException


class FallbackFailed(RuntimeError):
    """Raised when a fallback matcher fails to handle an event."""

    def __init__(self, *value: object):
        super().__init__(value)


__all__ = [
    "CancelException",
    "FallbackFailed",
    "MatcherException",
    "PassException",
]  # for backward compatibility
