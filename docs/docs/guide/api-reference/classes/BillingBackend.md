# BillingBackend

Abstract base class for the optional external sink that receives per-request billing records.

## Description

`BillingBackend` is an **optional mirror, not the default persistence path**. Every record already travels inside [`MemoryModel.billing`](MemoryModel.md), so a session's cost history survives through the normal memory commit without any billing backend at all. Implement this interface only when the same records must additionally reach an external cost store (database, metrics pipeline, quota enforcer).

The granularity is a single run: `commit_billing` is called once at the end of a run, with every record that run produced.

## Methods

### `commit_billing(session_id: str, records: list[BillingRecord]) -> None`

Append the records produced by one run.

**Parameters**:

- `session_id` (str): The session identifier
- `records` (list[[BillingRecord](BillingRecord.md)]): The run's records, in recording order

### `load_billing(session_id: str) -> list[BillingRecord]`

Return the records previously committed for a session.

**Parameters**:

- `session_id` (str): The session identifier

**Returns**: list[[BillingRecord](BillingRecord.md)] - The records stored for that session

## Built-in Implementations

- `NullBillingBackend`: no-op sink; records stay in memory only
- [`LegacyBackend`](LegacyBackend.md): in-process store guarded by a lock; also the default value of [`BackendSlots.billing`](BackendSlots.md)

## Wiring a Custom Sink

```python
from amrita_core import BackendSlots, BillingBackend, BillingRecord, LegacyBackend


class MyBillingSink(BillingBackend):
    async def commit_billing(
        self, session_id: str, records: list[BillingRecord]
    ) -> None:
        await my_db.insert_many(session_id, records)

    async def load_billing(self, session_id: str) -> list[BillingRecord]:
        return await my_db.fetch(session_id)


backend = LegacyBackend()
slot = BackendSlots(ability=backend, memory=backend, billing=MyBillingSink())
```

## When It Runs

`COMMIT_MEMORY` is the terminal workflow node and performs three steps in order:

1. Move the run's ledger into `memory.billing` (`SessionUsageProxy.flush_into`)
2. Commit memory through `slot.memory`
3. Hand the same records to `slot.billing`

Setting `DatabackendOptions.skip_billing_commit = True` skips only step 3, so memory still carries the records.

## Next

[BillingRecord](BillingRecord.md) - the record shape, or [RateConfig](RateConfig.md) - the pricing snapshot.
