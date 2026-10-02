"""Framework-level exception types.

```mermaid
flowchart LR
    A[provider rejects the request] --> B{is_context_overflow_error}
    B -->|yes| C[ContextOverflowError]
    B -->|no| D[ordinary failure / preset fallback]
```
"""

import re

__all__ = ["ContextOverflowError", "is_context_overflow_error"]


class ContextOverflowError(RuntimeError):
    """Raised when a provider rejects a request for exceeding its context window."""


#: Providers report this in prose rather than a machine-readable code, so the check is a pattern match over the message.
_OVERFLOW_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"maximum context length",
        r"context[_ ]length[_ ]exceeded",
        r"context window exceed",
        r"exceed[s]? the (maximum )?(model'?s )?context",
        r"prompt is too long",
        r"input is too long",
        r"input length and `?max_tokens`? exceed",
        r"too many tokens",
        r"reduce the length of the messages",
        r"maximum number of tokens",
    )
)


def is_context_overflow_error(error: BaseException) -> bool:
    """Whether an error looks like a provider context-window rejection.

    Deliberately conservative: mistaking a transient failure for an overflow
    would throw away history for nothing, so only well-known phrasings match.
    """
    text = str(error)
    return any(pattern.search(text) for pattern in _OVERFLOW_PATTERNS)
