class MatcherException(Exception):
    """Base exception for Matcher."""


class BlockException(MatcherException):
    pass


class CancelException(MatcherException):
    pass


class PassException(MatcherException):
    pass
