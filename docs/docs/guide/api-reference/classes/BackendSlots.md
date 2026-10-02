# BackendSlots

The `BackendSlots` dataclass holds the two backend references used by `ChatObject` at runtime for data I/O.

## Description

`BackendSlots` is a simple dataclass that bundles an [AbilityBackend](AbilityBackend.md) and a [MemoryBackend](MemoryBackend.md) together so they can be passed as a single argument to `ChatObject` or `AgentRuntime`.

## Fields

- `ability` ([AbilityBackend](AbilityBackend.md)): Backend responsible for loading tools, MCP clients, and presets
- `memory` ([MemoryBackend](MemoryBackend.md)): Backend responsible for loading and committing conversation memory
- `billing` ([BillingBackend](BillingBackend.md)): Optional sink for per-request billing records. Defaults to a `LegacyBackend`, so the slot is never `None`

## Usage

```python
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

bkd = LegacyBackend()
slot = BackendSlots(ability=bkd, memory=bkd)

# Pass to ChatObject
chat = ChatObject(
    train=train,
    user_input="Hello",
    session_id="my_session",
    backend=slot,
)
```

## Default Behavior

When `backend=None` is passed to `ChatObject` or `AgentRuntime`, `BackendSlots.default()` builds all three slots from **one shared** `LegacyBackend` instance:

```python
bkd = LegacyBackend()
slot = BackendSlots(ability=bkd, memory=bkd, billing=bkd)
```

This uses in-process containers for ability, memory and billing storage.

> `billing` is the only field with a default, and it has its own independent fallback: leaving it out of a hand-built `BackendSlots` constructs a fresh `LegacyBackend` just for billing, which does **not** share state with the `ability` / `memory` backends you passed in.
