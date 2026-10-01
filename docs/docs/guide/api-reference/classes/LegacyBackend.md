# LegacyBackend

The default built-in backend that implements [AbilityBackend](AbilityBackend.md), [MemoryBackend](MemoryBackend.md) and [BillingBackend](BillingBackend.md) using in-process containers.

## Description

`LegacyBackend` is the default backend used when no custom backend is provided. It preserves the original AmritaCore behavior where tools, presets, MCP clients, and memory are stored in global in-process containers. This is suitable for single-process applications and testing.

## Inheritance

`LegacyBackend` implements [AbilityBackend](AbilityBackend.md), [MemoryBackend](MemoryBackend.md) and [BillingBackend](BillingBackend.md).

## Constructor

```python
LegacyBackend()
```

## Behavior

- **Ability methods** (`load_ability_all`, `load_mcp_clients`, `load_tools`, `load_presets`): All return references to a shared global `AbilityContext` singleton (`LegacyBackend.glb`)
- **Memory methods** (`load_memory`, `commit_memory`): Read from and write to a `MemoryModel` field, scoped per `LegacyBackend` instance
- **Billing methods** (`commit_billing`, `load_billing`): Append to and read from a per-session in-process record store guarded by a lock

## Usage

```python
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.base.backend import BackendSlots

backend = LegacyBackend()
slot = BackendSlots(ability=backend, memory=backend, billing=backend)
```
