"""Session-scoped usage ledger with a stateless proxy handle.

The gateway layer (``libchat``) records every provider usage sample into a
run-scoped ledger through a :class:`SessionUsageProxy`.  The proxy is
stateless (``stream_id`` only) and re-resolves the ledger on every access,
so it is safe to pass around and store without risking reference splits.

Ledger lifecycle is tied to ``ChatObject._entry``: registered when the run
starts, snapshotted onto the ChatObject and unregistered (``dict.pop``) in
the ``finally`` block, so the process-wide registry never leaks.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import ClassVar

from pydantic import BaseModel, Field

from amrita_core.types.response import UniResponseUsage


class UsageEntry(BaseModel):
    """Immutable record of one provider-reported usage sample."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cache_hit: int | None = None
    cache_creation: int | None = None
    model: str | None = None
    request_id: str | None = None
    ts: float = Field(default_factory=time.time)


class UsageLedger:
    """Append-only collection of usage entries for one run."""

    __slots__ = ("_entries",)

    def __init__(self) -> None:
        self._entries: list[UsageEntry] = []

    def add(self, entry: UsageEntry) -> None:
        """Append one entry (never mutated after insert)."""
        self._entries.append(entry)

    def entries(self) -> list[UsageEntry]:
        """Copy of all entries, so callers cannot mutate the ledger."""
        return list(self._entries)

    def total(self) -> UniResponseUsage[int]:
        """Derived sum over all recorded entries (never hand-maintained)."""
        prompt = completion = total = 0
        cache_hit = cache_creation = 0
        for e in self._entries:
            prompt += e.prompt_tokens
            completion += e.completion_tokens
            total += e.total_tokens
            cache_hit += e.cache_hit or 0
            cache_creation += e.cache_creation or 0
        return UniResponseUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
            cache_hit=cache_hit or None,
            cache_creation=cache_creation or None,
        )

    def prompt_since(self, since_ts: float) -> int:
        """Sum of prompt tokens recorded at or after ``since_ts``.

        Used as the Step-window prompt-token count for budget checks and
        between-Step compression thresholds.
        """
        return sum(e.prompt_tokens for e in self._entries if e.ts >= since_ts)


class UsageSnapshot(BaseModel):
    """Serializable snapshot of a run's ledger, kept on the ChatObject."""

    stream_id: str
    entries: list[UsageEntry]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    @classmethod
    def from_ledger(cls, stream_id: str, ledger: UsageLedger) -> "UsageSnapshot":
        total = ledger.total()
        return cls(
            stream_id=stream_id,
            entries=ledger.entries(),
            prompt_tokens=total.prompt_tokens,
            completion_tokens=total.completion_tokens,
            total_tokens=total.total_tokens,
        )


class UsageRegistry:
    """Process-wide ledger registry keyed by ``stream_id`` (run-scoped).

    ``unregister`` only pops the dictionary entry; the snapshot kept on the
    ChatObject preserves the run data after the registry releases it.
    """

    _ledgers: ClassVar[dict[str, UsageLedger]] = {}
    _lock: ClassVar[Lock] = Lock()

    @classmethod
    def register(cls, stream_id: str) -> "SessionUsageProxy":
        """Create (or reuse) the ledger for a run and return its proxy."""
        with cls._lock:
            cls._ledgers.setdefault(stream_id, UsageLedger())
        return SessionUsageProxy(stream_id)

    @classmethod
    def unregister(cls, stream_id: str) -> None:
        """Drop the ledger from the process-wide registry (idempotent)."""
        with cls._lock:
            cls._ledgers.pop(stream_id, None)

    @classmethod
    def _ledger(cls, stream_id: str) -> UsageLedger | None:
        with cls._lock:
            return cls._ledgers.get(stream_id)


class SessionUsageProxy:
    """Stateless handle to the run-scoped ledger.

    Every access re-resolves the ledger by ``stream_id``, so the proxy holds
    no mutable reference: copies, argument passing and storage are all safe
    from reference-split bugs.
    """

    __slots__ = ("stream_id",)

    def __init__(self, stream_id: str) -> None:
        self.stream_id = stream_id

    def record(
        self,
        usage: UniResponseUsage | None,
        *,
        model: str | None = None,
        request_id: str | None = None,
    ) -> None:
        """Record one provider usage sample into the run's ledger.

        No-op when the ledger is gone (run finished) or usage is ``None``.
        """
        ledger = UsageRegistry._ledger(self.stream_id)
        if ledger is None or usage is None:
            return
        ledger.add(
            UsageEntry(
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
                total_tokens=usage.total_tokens or 0,
                cache_hit=usage.cache_hit,
                cache_creation=usage.cache_creation,
                model=model,
                request_id=request_id,
            )
        )

    @property
    def extra_total(self) -> UniResponseUsage[int]:
        """Derived total of the run's execution-process usage.

        This is the workflow-internal usage (strategy tool rounds plus
        auxiliary calls) — distinct from the final completion's usage, which
        lives on ``resp.response.usage``.
        """
        ledger = UsageRegistry._ledger(self.stream_id)
        if ledger is None:
            return UniResponseUsage(
                prompt_tokens=0, completion_tokens=0, total_tokens=0
            )
        return ledger.total()

    def prompt_since(self, since_ts: float) -> int:
        """Prompt tokens recorded at or after ``since_ts`` (Step window)."""
        ledger = UsageRegistry._ledger(self.stream_id)
        if ledger is None:
            return 0
        return ledger.prompt_since(since_ts)

    def snapshot(self) -> UsageSnapshot | None:
        """Copy of the ledger for post-run inspection (kept on ChatObject)."""
        ledger = UsageRegistry._ledger(self.stream_id)
        if ledger is None:
            return None
        return UsageSnapshot.from_ledger(self.stream_id, ledger)


__all__ = [
    "SessionUsageProxy",
    "UsageEntry",
    "UsageLedger",
    "UsageRegistry",
    "UsageSnapshot",
]
