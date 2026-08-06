# ClientManager

The ClientManager class provides centralized management for multiple MCP (Model Context Protocol) server connections and tool registration.

## Overview

ClientManager is a **singleton class that extends [`MultiClientManager`](MultiClientManager.md)**, inheriting all of its functionality while adding singleton pattern support for global accessibility. It handles multiple MCP clients, resolves tool name conflicts through automatic remapping, routes tool calls to appropriate servers, and automatically registers all discovered tools into the ToolsManager.

## Inheritance

```text
ClientManager → MultiClientManager
```

ClientManager inherits all methods and properties from MultiClientManager and adds:

- Singleton instance management via `__new__()`
- Global single-instance access pattern

## Properties

_Inherited from [`MultiClientManager`](MultiClientManager.md):_

- `clients` (list[MCPClient]): List of all registered MCP clients
- `script_to_clients` (dict[str, MCPClient]): Mapping from server script paths to clients
- `name_to_clients` (dict[str, MCPClient]): Mapping from tool names to their owning clients
- `tools_remapping` (dict[str, str]): Tool name remapping (original → remapped)
- `reversed_remappings` (dict[str, str]): Reverse remapping (remapped → original)
- `tools_manager` (MultiToolsManager): The tool manager where MCP tools are registered
- `_is_initialized` (bool): Whether all clients have been initialized

## Methods

### `__new__() -> Self`

Creates or returns the singleton instance of ClientManager.

**Returns:**

- `Self`: The singleton instance

**Note:** ClientManager implements the singleton pattern - only one instance exists per application. Every call to `ClientManager()` returns the same instance.

**Example:**

```python
from amrita_core.tools.mcp import ClientManager

manager1 = ClientManager()
manager2 = ClientManager()
print(manager1 is manager2)  # True - same instance
```

### `__init__() -> None`

Initializes the ClientManager (runs only once due to singleton pattern).

**Note:** Initialization logic executes only on the first instantiation.

_All other methods are inherited from [`MultiClientManager`](MultiClientManager.md):_

- `get_client_by_script(server_script)` - Get client by server script
- `get_client_by_tool_name(tool_name)` - Find client owning a specific tool
- `register_only(client)` / `register_only(server_script)` - Register without initializing
- `initialize_this(server_script)` - Register and initialize single server
- `initialize_scripts_all(scripts)` - Initialize multiple servers
- `initialize_all()` - Connect to all registered servers
- `update_tools(client)` - Update tools from a client
- `unregister_client(script_name)` - Remove a server
- `reinitialize_all()` - Refresh all connections

See [`MultiClientManager`](MultiClientManager.md) documentation for detailed method descriptions.

## Complete Usage Example

```python
import asyncio
from amrita_core.tools.mcp import ClientManager


async def main():
    # Get the singleton instance
    manager = ClientManager()

    # Method 1: Configuration-based setup (recommended)
    # See AmritaConfig for declarative configuration

    # Method 2: Programmatic setup
    scripts = ["/path/to/weather.mcp", "/path/to/database.mcp", "/path/to/calendar.mcp"]

    # Register and initialize all servers
    await manager.initialize_scripts_all(scripts)

    # Check available tools
    available_tools = manager.tools_manager.get_tools()
    print(f"Available tools: {list(available_tools.keys())}")

    # Find which client owns a tool
    weather_client = await manager.get_client_by_tool_name("get_weather")
    print(f"Tool owner: {weather_client.server_script}")

    # Handle duplicate tool names (automatic remapping)
    # If two servers have "search" tool, second one becomes "referred_42_search"

    # Dynamically add a new server
    await manager.initialize_this("/dynamic/new-server.mcp")

    # Remove a server
    await manager.unregister_client("/path/to/old-server.mcp")

    # Reinitialize all (refresh connections)
    await manager.reinitialize_all()


asyncio.run(main())
```

## Key Features

### Automatic Tool Registration

All tools from registered MCP servers are automatically added to `ToolsManager` and become available to agents.

### Tool Name Conflict Resolution

When multiple servers provide tools with the same name:

- First registration keeps original name
- Subsequent registrations are auto-remapped (e.g., `referred_42_search`)
- Warning logs are generated for conflicts

### Intelligent Routing

When a tool is called, `ClientManager` automatically routes the request to the correct MCP server based on tool name mapping.

### Thread Safety

All operations are protected by an async lock (`_lock`) to ensure thread-safe access to shared state.

### Lifecycle Management

Handles connection establishment, tool discovery, registration, and cleanup for multiple servers simultaneously.

## Error Handling

- **Server initialization failure**: Logs error, continues with other servers (unless `fail_then_raise=True`)
- **Tool execution errors**: Handled by individual `MCPClient`, returns structured error JSON
- **Duplicate tools**: Auto-remapped with warning logs
- **Connection loss**: Automatic retry on next tool call

## Related Documentation

- [MCPClient](MCPClient.md) - Individual client management
- [ToolsManager](ToolsManager.md) - Tool registration system
- [MCP Server Integration](../../guide/extensions-integration/mcp-server-integration.md) - Comprehensive integration guide
- [AmritaConfig](AmritaConfig.md) - Configuration-based setup
