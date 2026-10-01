# NullBillingBackend

A no-op billing sink; records stay in memory only.

## Description

`NullBillingBackend` implements every [`BillingBackend`](BillingBackend.md) method as a no-op. Bind it when you want to explicitly opt out of forwarding billing records anywhere, rather than leaving `BackendSlots.billing` at its default.

Note that **omitting the billing backend is already harmless**: records still accumulate on `MemoryModel.billing`, which is the default persistence path. `NullBillingBackend` exists for the case where you want that intent to be visible in the code, and for tests that need a backend which provably does nothing.

## Methods

### `async commit_billing(session_id, records) -> None`

Returns immediately. Discards the records.

### `async load_billing(session_id) -> list[BillingRecord]`

Always returns an empty list.

## Usage

```python
from amrita_core import BackendSlots, LegacyBackend, NullBillingBackend

backend = LegacyBackend()
slot = BackendSlots(
    ability=backend,
    memory=backend,
    billing=NullBillingBackend(),  # explicit "do not mirror anywhere"
)
```

## Related

- [BillingBackend](BillingBackend.md) — the interface
- [LegacyBackend](LegacyBackend.md) — the default billing sink
- [BackendSlots](BackendSlots.md) — the slot that carries it
