# AbilityBackend

Abstract base class for backends that provide ability-related data (tools, MCP clients, presets).

## Description

`AbilityBackend` defines the interface for loading ability context from a persistence layer. Subclasses must implement all four methods.

## Methods

### `load_ability_all(session_id: str) -> AbilityContext`

Load the full ability context for a given session.

**Parameters**:

- `session_id` (str): The session identifier

**Returns**: [AbilityContext](AbilityContext.md) - The complete ability context

### `load_mcp_clients(session_id: str) -> MultiClientManager`

Load MCP clients for a given session.

**Parameters**:

- `session_id` (str): The session identifier

**Returns**: `MultiClientManager` - The MCP client manager

### `load_tools(session_id: str) -> MultiToolsManager`

Load tools for a given session.

**Parameters**:

- `session_id` (str): The session identifier

**Returns**: `MultiToolsManager` - The tools manager

### `load_presets(session_id: str) -> MultiPresetManager`

Load presets for a given session.

**Parameters**:

- `session_id` (str): The session identifier

**Returns**: `MultiPresetManager` - The presets manager

## Built-in Implementation

- [`LegacyBackend`](LegacyBackend.md): Default in-process implementation that stores data in global containers
