"""Framework-level exception types.

```mermaid
flowchart LR
    A[provider rejects the request] --> B{is_context_overflow_error}
    B -->|yes| C[ContextOverflowError]
    B -->|no| D[AdapterError]
    D --> E[preset fallback / caller]
```
"""

from __future__ import annotations

import functools
import inspect
import re
from collections.abc import AsyncGenerator, Callable
from typing import Any, Literal


class ContextOverflowError(RuntimeError):
    """Raised when a provider rejects a request for exceeding its context window."""


class AdapterError(RuntimeError):
    """Base class for every failure raised by an adapter.

    The framework only ever sees this shape, whatever SDK the adapter wraps.
    ``original`` keeps the provider/SDK exception untouched so callers that
    need the raw status code, headers or error body can still reach it; the
    normalized message is what gets logged and matched by the fallback loop.

    Adapters must never leak a bare SDK exception: a caller cannot tell an
    ``openai.RateLimitError`` from an ``anthropic.RateLimitError`` without
    importing both, and the preset-fallback layer has no way to classify them.
    """

    def __init__(
        self,
        message: str,
        *,
        original: BaseException | None = None,
        adapter: str | None = None,
        protocol: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        # The untouched SDK/provider exception, when this error wraps one.
        self.original = original
        # Adapter class or protocol that raised, for logs.
        self.adapter = adapter
        self.protocol = protocol
        # HTTP status when the provider answered with one.
        self.status_code = status_code

    def __str__(self) -> str:
        return self.message


class AdapterRequestError(AdapterError):
    """The provider rejected the request (4xx/5xx, malformed body)."""


class AdapterAuthError(AdapterRequestError):
    """Credentials are missing, invalid or lack permission."""


class AdapterRateLimitError(AdapterRequestError):
    """The provider throttled the request; retrying later may help."""


class AdapterTimeoutError(AdapterError):
    """The request exceeded the configured timeout."""


class AdapterConnectionError(AdapterError):
    """The provider could not be reached (DNS, TLS, socket)."""


class AdapterResponseError(AdapterError):
    """The provider answered with something the adapter cannot interpret."""


class UnsupportedContentError(AdapterError):
    """The payload carries content the target adapter's wire format cannot hold.

    Raised *before* a request is sent, so the failure is attributable to the
    capability declaration rather than to the provider. The agent loop catches
    it, replaces the offending blocks with :attr:`notice` and lets the model
    decide what to do next instead of silently dropping the media.
    """

    def __init__(
        self,
        message: str | None = None,
        *,
        protocol: str,
        scope: Literal["tool_result", "input"],
        kinds: tuple[str, ...] = (),
        tool_call_ids: tuple[str, ...] = (),
        adapter: str | None = None,
        original: BaseException | None = None,
    ) -> None:
        self.scope = scope
        self.kinds = kinds
        self.tool_call_ids = tool_call_ids
        if message is None:
            kind_text = ", ".join(kinds) or "non-text"
            where = (
                f"tool result(s) {', '.join(tool_call_ids)}"
                if tool_call_ids
                else "the outgoing payload"
            )
            message = (
                f"Adapter `{protocol}` cannot carry {kind_text} content in {where};"
                f" the adapter declares no {scope}_multimodal support."
            )
        super().__init__(message, adapter=adapter, protocol=protocol, original=original)

    @property
    def notice(self) -> str:
        """Text handed back to the model in place of the untransportable blocks."""
        kind_text = ", ".join(self.kinds) or "non-text"
        return (
            f"ERR: this tool returned {kind_text} content, but the current adapter"
            f" (`{self.protocol}`) cannot carry it in a tool result. Return a"
            " text-only result instead (for example a URL or a short description),"
            " or use another tool."
        )


# Providers report context overflow in prose rather than a machine-readable code, so the check is a pattern match over the message.
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

    Walks the ``original`` chain so a normalized :class:`AdapterError` still
    matches on the provider's own wording. Deliberately conservative: mistaking
    a transient failure for an overflow would throw away history for nothing,
    so only well-known phrasings match.
    """
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if any(pattern.search(str(current)) for pattern in _OVERFLOW_PATTERNS):
            return True
        current = getattr(current, "original", None) or current.__cause__
    return False


# SDK exception class names -> normalized type; name-based so neither SDK is imported.
_BY_NAME: dict[str, type[AdapterError]] = {
    "AuthenticationError": AdapterAuthError,
    "PermissionDeniedError": AdapterAuthError,
    "RateLimitError": AdapterRateLimitError,
    "APITimeoutError": AdapterTimeoutError,
    "APIConnectionError": AdapterConnectionError,
    "InternalServerError": AdapterResponseError,
    "APIStatusError": AdapterRequestError,
    "BadRequestError": AdapterRequestError,
    "NotFoundError": AdapterRequestError,
    "UnprocessableEntityError": AdapterRequestError,
    "APIResponseValidationError": AdapterResponseError,
}

_BY_STATUS: dict[int, type[AdapterError]] = {
    401: AdapterAuthError,
    403: AdapterAuthError,
    429: AdapterRateLimitError,
}


def normalize_adapter_error(
    error: BaseException,
    *,
    adapter: str | None = None,
    protocol: str | None = None,
) -> AdapterError:
    """Translate any exception into the framework's adapter error shape.

    Already-normalized errors pass through untouched, so wrapping a call twice
    does not stack prefixes or lose the original.
    """
    if isinstance(error, AdapterError):
        return error
    status = getattr(error, "status_code", None)
    status_code = status if isinstance(status, int) else None
    name = type(error).__name__
    error_type = (
        _BY_NAME.get(name)
        or (_BY_STATUS.get(status_code) if status_code is not None else None)
        or AdapterError
    )
    detail = str(error).strip() or name
    label = adapter or protocol or "adapter"
    return error_type(
        f"[{label}] {detail}",
        original=error,
        adapter=adapter,
        protocol=protocol,
        status_code=status_code,
    )


def normalize_adapter_errors(
    adapter: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorate an adapter method so every failure leaves normalized.

    Handles plain coroutines and async generators: the latter must stay lazy,
    so the wrapper iterates instead of awaiting. ``AdapterError`` is re-raised
    as-is, and ``KeyboardInterrupt``/``CancelledError`` are not ``Exception``
    subclasses, so cancellation still propagates untouched.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.isasyncgenfunction(func):

            @functools.wraps(func)
            async def async_gen_wrapper(
                *args: Any, **kwargs: Any
            ) -> AsyncGenerator[Any, None]:
                try:
                    async for item in func(*args, **kwargs):
                        yield item
                except AdapterError:
                    raise
                except Exception as exc:
                    raise normalize_adapter_error(exc, adapter=adapter) from exc

            return async_gen_wrapper

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except AdapterError:
                raise
            except Exception as exc:
                raise normalize_adapter_error(exc, adapter=adapter) from exc

        return async_wrapper

    return decorator


__all__ = [
    "AdapterAuthError",
    "AdapterConnectionError",
    "AdapterError",
    "AdapterRateLimitError",
    "AdapterRequestError",
    "AdapterResponseError",
    "AdapterTimeoutError",
    "ContextOverflowError",
    "UnsupportedContentError",
    "is_context_overflow_error",
    "normalize_adapter_error",
    "normalize_adapter_errors",
]
