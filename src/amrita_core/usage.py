"""Run-scoped billing ledger with an optional external sink.

Every provider request that reports usage appends one :class:`BillingRecord`
to the run's ledger. The ledger lives in process memory for the duration of
the run so hot-path reads (totals, step windows) stay synchronous, and is
handed to a :class:`BillingBackend` once, at the run boundary.

The same records also travel inside ``MemoryModel.billing``, which is the
default persistence path; the backend exists only for consumers that need to
mirror the data into an external cost store.
"""

from __future__ import annotations

import time

from amrita_core.base.backend import BillingBackend
from amrita_core.types.billing import BillingRecord, RateConfig
from amrita_core.types.response import UniResponseUsage


class SessionUsageProxy:
    """Handle to one run's billing ledger.

    ``record`` and every read are synchronous because the ledger is a plain
    in-process list; only :meth:`commit` crosses the async boundary to the
    backend.
    """

    __slots__ = ("_backend", "_flushed", "_records", "session_id", "stream_id")

    def __init__(
        self,
        session_id: str,
        stream_id: str,
        backend: BillingBackend | None = None,
        records: list[BillingRecord] | None = None,
    ) -> None:
        """Create a ledger for one run.

        Args:
            session_id: Session the run belongs to.
            stream_id: Unique id of this run.
            backend: Optional external sink that receives the records.
            records: Optional pre-existing list to append to.
        """
        self.session_id = session_id
        self.stream_id = stream_id
        self._backend = backend
        self._records: list[BillingRecord] = records if records is not None else []
        self._flushed = 0

    def record(
        self,
        usage: UniResponseUsage | None,
        *,
        model: str | None = None,
        preset_name: str | None = None,
        rate: RateConfig | None = None,
        request_id: str | None = None,
    ) -> None:
        """Append one provider usage sample to the run ledger."""
        if usage is None:
            return
        self._records.append(
            BillingRecord(
                model=model,
                preset_name=preset_name,
                rate=rate,
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
                total_tokens=usage.total_tokens or 0,
                cache_hit=usage.cache_hit,
                cache_creation=usage.cache_creation,
                session_id=self.session_id,
                stream_id=self.stream_id,
                request_id=request_id,
                ts=time.time(),
            )
        )

    @property
    def records(self) -> list[BillingRecord]:
        """Copy of the run's records, so callers cannot mutate the ledger."""
        return list(self._records)

    @property
    def extra_total(self) -> UniResponseUsage[int]:
        """Derived sum over every record in the run."""
        prompt = completion = total = 0
        for record in self._records:
            prompt += record.prompt_tokens
            completion += record.completion_tokens
            total += record.total_tokens
        return UniResponseUsage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
        )

    def prompt_since(self, since_ts: float) -> int:
        """Prompt tokens recorded at or after ``since_ts``, summed.

        This is the *spend* reading: every request carries the whole context it
        sent, so the sum answers "how much prompt did this run push through the
        provider since ``since_ts``". It is not the size of the history — for
        that see :meth:`latest_prompt_since`, which is what window and budget
        checks want.
        """
        return sum(r.prompt_tokens for r in self._records if r.ts >= since_ts)

    def latest_prompt_since(self, since_ts: float) -> int:
        """Prompt tokens of the most recent request at or after ``since_ts``.

        The window reading: one request reports the size of the context it
        carried, so the latest record is how large the history has grown to,
        while :meth:`prompt_since` is what the run has spent. A Step issues
        several requests (one per tool-call round, plus its summary call), and
        summing them would count the same history once per request.

        Returns ``0`` when no request was recorded in the window.
        """
        for record in reversed(self._records):
            if record.ts >= since_ts:
                return record.prompt_tokens
        return 0

    def flush_into(self, target: list[BillingRecord]) -> None:
        """Append records not yet flushed to ``target``.

        Idempotent: calling it twice only appends the newly recorded samples,
        so a retried commit node cannot duplicate the conversation ledger.
        """
        if self._flushed >= len(self._records):
            return
        target.extend(self._records[self._flushed :])
        self._flushed = len(self._records)

    async def commit(self) -> None:
        """Hand the run's records to the external sink, if one is bound."""
        if self._backend is None:
            return
        await self._backend.commit_billing(self.session_id, self._records)


__all__ = ["SessionUsageProxy"]
