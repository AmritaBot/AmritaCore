# AbilityContext

A dataclass that holds the ability-related state for a `ChatObject` runtime session.

## Description

`AbilityContext` bundles the tools, presets, MCP clients, and extra settings that define what a `ChatObject` can do during a session.

## Fields

- `tools` ([MultiToolsManager](MultiToolsManager.md)): Manager for tools available in the session. Defaults to the global `ToolsManager()` singleton
- `presets` ([MultiPresetManager](MultiPresetManager.md)): Manager for model presets in the session. Defaults to the global `PresetManager()` singleton
- `mcp` ([MultiClientManager](MultiClientManager.md)): Manager for MCP client connections. Defaults to the global `ClientManager()` singleton
- `extra` (dict[str, Any]): Additional custom data associated with the ability context

## Default Behavior

Each field defaults to the corresponding global manager singleton, which is shared across all sessions. To use session-isolated managers, replace the field with a fresh `MultiToolsManager()`, `MultiPresetManager()`, or `MultiClientManager()` instance.

## Usage

```python
from amrita_core.contexts import AbilityContext

ctx = AbilityContext()
# All fields default to global singletons
print(ctx.tools)  # ToolsManager singleton
print(ctx.presets)  # PresetManager singleton
```
