# BackendSlots

The `BackendSlots` dataclass holds the two backend references used by `ChatObject` at runtime for data I/O.

## Description

`BackendSlots` is a simple dataclass that bundles an [AbilityBackend](AbilityBackend.md) and a [MemoryBackend](MemoryBackend.md) together so they can be passed as a single argument to `ChatObject` or `AgentRuntime`.

## Fields

- `ability` ([AbilityBackend](AbilityBackend.md)): Backend responsible for loading tools, MCP clients, and presets
- `memory` ([MemoryBackend](MemoryBackend.md)): Backend responsible for loading and committing conversation memory

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

When `backend=None` is passed to `ChatObject` or `AgentRuntime`, the default is:

```python
bkd = LegacyBackend()
slot = BackendSlots(bkd, bkd)
```

This uses in-process global containers for both memory and ability storage.
