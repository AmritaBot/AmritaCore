class MatcherException(Exception):
    """Base exception for Matcher."""


class BlockException(MatcherException):
    pass


class CancelException(MatcherException):
    pass


class PassException(MatcherException):
    pass


class FallbackFailed(RuntimeError):
    """Raised when a fallback matcher fails to handle an event."""

    def __init__(self, *value: object):
        super().__init__(value)
