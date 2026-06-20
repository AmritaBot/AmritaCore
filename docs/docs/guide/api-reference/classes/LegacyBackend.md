# LegacyBackend

The default built-in backend that implements both [AbilityBackend](AbilityBackend.md) and [MemoryBackend](MemoryBackend.md) using in-process global containers.

## Description

`LegacyBackend` is the default backend used when no custom backend is provided. It preserves the original AmritaCore behavior where tools, presets, MCP clients, and memory are stored in global in-process containers. This is suitable for single-process applications and testing.

## Inheritance

`LegacyBackend` implements both [AbilityBackend](AbilityBackend.md) and [MemoryBackend](MemoryBackend.md).

## Constructor

```python
LegacyBackend(ctx: StateContext | None = None)
```

**Parameters**:

- `ctx` ([StateContext](StateContext.md) | None, optional): An optional pre-built state context. If not provided, a new one is created lazily when memory operations are performed

## Behavior

- **Ability methods** (`load_ability_all`, `load_mcp_clients`, `load_tools`, `load_presets`): All return references to a shared global `AbilityContext` singleton (`LegacyBackend.glb`)
- **Memory methods** (`load_memory`, `commit_memory`): Read from and write to an internal `StateContext` instance, scoped per `LegacyBackend` instance

## Usage

```python
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.base.backend import BackendSlots

backend = LegacyBackend()
slot = BackendSlots(ability=backend, memory=backend)
```
