# MultiClientManager

The MultiClientManager class provides the base functionality for managing multiple MCP (Model Context Protocol) server connections and tool registration.

## Overview

MultiClientManager handles the complexity of connecting to multiple MCP servers, discovering their tools, resolving naming conflicts through automatic remapping, and registering all tools into a centralized ToolsManager. It serves as the foundation for ClientManager's singleton implementation.

## Properties

- `clients` (list[MCPClient]): List of all registered MCP clients
- `script_to_clients` (dict[str, MCPClient]): Mapping from server script paths to client instances
- `name_to_clients` (dict[str, MCPClient]): Mapping from tool names to their owning clients
- `tools_remapping` (dict[str, str]): Tool name remapping dictionary (original_name → remapped_name)
- `reversed_remappings` (dict[str, str]): Reverse remapping dictionary (remapped_name → original_name)
- `tools_manager` (MultiToolsManager): The tool manager where MCP tools are registered
- `_is_initialized` (bool): Whether all clients have been initialized
- `_lock` (asyncio.Lock): Async lock for thread-safe operations

## Methods

### `__init__() -> None`

Initializes a new MultiClientManager instance.

**Example:**

```python
from amrita_core.tools.mcp import MultiClientManager

manager = MultiClientManager()
```

### `get_client_by_script(server_script: str | Path) -> MCPClient`

Creates a new MCP client for a specific server script without registering it.

**Parameters:**

- `server_script`: Path to the MCP server script or URI

**Returns:**

- `MCPClient`: A new, unconnected client instance

**Example:**

```python
client = manager.get_client_by_script("/path/to/server.mcp")
```

### `async get_client_by_tool_name(tool_name: str) -> MCPClient`

Finds the MCP client that owns a specific tool by its name.

**Parameters:**

- `tool_name`: Name of the tool (automatically handles remapped names)

**Returns:**

- `MCPClient`: The client instance that manages this tool

**Raises:**

- `RuntimeError`: If the tool is not found in any registered client

**Example:**

```python
client = await manager.get_client_by_tool_name("get_weather")
print(f"Tool owner: {client.server_script}")
```

### `register_only(*, client: MCPClient) -> Self`

Registers an MCP client without initializing it.

**Parameters:**

- `client`: Pre-created MCP client instance

**Returns:**

- `Self`: For method chaining

**Example:**

```python
custom_client = MCPClient("/special/server.mcp")
manager.register_only(client=custom_client)
```

### `register_only(*, server_script: str | Path) -> Self`

Registers an MCP server by script path without initializing it.

**Parameters:**

- `server_script`: Path to the MCP server script

**Returns:**

- `Self`: For method chaining

**Example:**

```python
manager.register_only(server_script="/path/to/server.mcp")
```

### `async initialize_this(server_script: str | Path, fail_then_raise: bool = False) -> Self`

Registers and initializes a single MCP server.

**Parameters:**

- `server_script`: Path to the MCP server script
- `fail_then_raise`: If True, raises exceptions on initialization failure

**Returns:**

- `Self`: For method chaining

**Example:**

```python
await manager.initialize_this("/path/to/weather.mcp")
```

### `async initialize_scripts_all(scripts: Iterable[str | Path]) -> Self`

Initializes multiple MCP servers from an iterable of script paths.

**Parameters:**

- `scripts`: Iterable of server script paths

**Returns:**

- `Self`: For method chaining

**Example:**

```python
scripts = ["/path/to/weather.mcp", "/path/to/database.mcp"]
await manager.initialize_scripts_all(scripts)
```

### `async initialize_all(lock: bool = True) -> Self`

Connects to all registered MCP servers and registers their tools.

**Parameters:**

- `lock`: If True, acquires internal lock before initialization

**Returns:**

- `Self`: Sets `_is_initialized` to True upon completion

**Example:**

```python
# Register servers first
manager.register_only(server_script="/server1.mcp")
manager.register_only(server_script="/server2.mcp")

# Then initialize all at once
await manager.initialize_all()
```

### `async update_tools(client: MCPClient) -> Self`

Updates tools from a specific client, re-registering them with conflict resolution.

**Parameters:**

- `client`: The client whose tools should be updated

**Returns:**

- `Self`: For method chaining

**Example:**

```python
await manager.update_tools(existing_client)
```

### `async unregister_client(script_name: str | Path, lock: bool = True) -> None`

Unregisters an MCP server and removes all its tools from the tools manager.

**Parameters:**

- `script_name`: Path to the server script to remove
- `lock`: If True, acquires internal lock during operation

**Example:**

```python
await manager.unregister_client("/path/to/remove.mcp")
```

### `async reinitialize_all() -> None`

Reinitializes all registered clients (useful for refreshing connections after failures).

**Example:**

```python
await manager.reinitialize_all()
```

### `_tools_wrapper(tool_name: str) -> Callable[[dict[str, Any]], Awaitable[str]]`

Creates a wrapper function for tool execution that can be registered as a tool handler.

**Parameters:**

- `tool_name`: Name of the tool to wrap

**Returns:**

- `Callable`: Async function that accepts tool arguments and returns results

**Note:** Internal method used for tool registration.

### `_load_this(client: MCPClient, fail_then_raise: bool = True) -> None`

Internal method to load tools from a client and register them with conflict resolution.

**Parameters:**

- `client`: The client whose tools should be loaded
- `fail_then_raise`: If True, raises exceptions on tool loading failure

**Note:** This is an internal method called during initialization.

## Key Features

### Automatic Tool Registration

All tools from registered MCP servers are automatically discovered and added to `tools_manager`, making them immediately available to agents.

### Tool Name Conflict Resolution

When multiple servers provide tools with identical names:

- First registration retains the original name
- Subsequent registrations are automatically remapped (e.g., `search` → `referred_42_search`)
- Warning logs are generated for each conflict detected
- Remapping information is stored in `tools_remapping` and `reversed_remappings` dictionaries

### Intelligent Routing

The `get_client_by_tool_name()` method automatically resolves which client owns a tool, handling both original and remapped names transparently.

### Thread Safety

All critical operations are protected by an async lock (`_lock`) to ensure thread-safe access to shared state when managing concurrent operations.

### Lifecycle Management

Handles the complete lifecycle of multiple MCP connections:

- Connection establishment
- Tool discovery and format conversion
- Tool registration with conflict handling
- Connection cleanup and reinitialization

## Complete Usage Example

```python
import asyncio
from amrita_core.tools.mcp import MultiClientManager

async def main():
    # Create manager instance
    manager = MultiClientManager()

    # Method 1: Programmatic setup
    scripts = [
        "/path/to/weather.mcp",
        "/path/to/database.mcp",
        "/path/to/calendar.mcp"
    ]

    # Register and initialize all servers
    await manager.initialize_scripts_all(scripts)

    # Check available tools
    available_tools = manager.tools_manager.get_tools()
    print(f"Available tools: {list(available_tools.keys())}")

    # Find which client owns a specific tool
    weather_client = await manager.get_client_by_tool_name("get_weather")
    print(f"Weather tool provided by: {weather_client.server_script}")

    # Handle duplicate tool names (automatic remapping)
    # If two servers both have a "search" tool:
    # - First server keeps "search"
    # - Second server becomes "referred_42_search"

    # Dynamically add a new server at runtime
    await manager.initialize_this("/dynamic/new-server.mcp")

    # Remove a server and its tools
    await manager.unregister_client("/path/to/old-server.mcp")

    # Refresh all connections (e.g., after network issues)
    await manager.reinitialize_all()

    # Manual client management
    custom_client = manager.get_client_by_script("/special/server.mcp")
    manager.register_only(client=custom_client)
    await manager.initialize_all()

asyncio.run(main())
```

## Error Handling

MultiClientManager includes robust error handling:

- **Server initialization failure**: Logs error and continues with other servers (unless `fail_then_raise=True`)
- **Tool execution errors**: Handled by individual MCPClient instances, returns structured error JSON
- **Duplicate tool names**: Automatically remapped with warning logs
- **Connection loss**: Automatic retry on next tool call via `reinitialize_all()`
- **Thread safety violations**: Prevented by async lock mechanism

## Relationship with ClientManager

[`ClientManager`](ClientManager.md) extends MultiClientManager and adds:

- **Singleton pattern**: Ensures only one instance exists per application
- **Global accessibility**: Can be accessed from anywhere via `ClientManager()`
- **Configuration integration**: Works seamlessly with AmritaConfig's MCP settings

For most use cases, prefer using ClientManager over directly instantiating MultiClientManager.

## Related Documentation

- [ClientManager](ClientManager.md) - Singleton wrapper for global access
- [MCPClient](MCPClient.md) - Individual client management
- [ToolsManager](ToolsManager.md) - Tool registration system
- [MCP Server Integration](../../guide/extensions-integration/mcp-server-integration.md) - Comprehensive integration guide
