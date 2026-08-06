# MCPClient

The MCPClient class provides a reusable client for connecting to and interacting with MCP (Model Context Protocol) servers.

## Overview

MCPClient handles individual MCP server connections, tool discovery, format conversion, and tool execution. It serves as the bridge between AmritaCore's tool system and external MCP-compliant services.

## Properties

- `mcp_client` (Client | None): The underlying FastMCP client instance
- `server_script` (str | Path): The MCP server script path or URI
- `tools` (list[MCPToolSchema]): List of original MCP tools fetched from the server
- `openai_tools` (list[ToolFunctionSchema]): List of tools converted to OpenAI-compatible format

## Methods

### `__init__(server_script: str | Path) -> None`

Initializes an MCP client for a specific server.

**Parameters:**

- `server_script`: Path to the MCP server script or URI

**Example:**

```python
from amrita_core.tools.mcp import MCPClient

client = MCPClient("/path/to/weather-server.mcp")
```

### `async __aenter__() -> Self`

Async context manager entry - connects to the MCP server.

**Returns:**

- `Self`: The client instance for method chaining

**Example:**

```python
async with MCPClient("/path/to/server.mcp") as client:
    tools = client.get_tools()
```

### `async __aexit__(exc_type, exc_val, exc_tb) -> None`

Async context manager exit - closes the connection.

### `async simple_call(tool_name: str, data: dict[str, Any]) -> str`

Calls an MCP tool and returns the result.

**Parameters:**

- `tool_name`: Name of the tool to call
- `data`: Dictionary of tool parameters

**Returns:**

- `str`: Tool execution result (text content)
- On error: JSON string with error details `{"success": False, "error": "..."}`

**Example:**

```python
result = await client.simple_call("get_weather", {"city": "New York"})
print(result)  # "Weather in New York: Sunny, 25°C"
```

### `async _connect(update_tools: bool = False) -> None`

Establishes connection to the MCP server.

**Parameters:**

- `update_tools`: If True, fetches and converts available tools

**Raises:**

- `RuntimeError`: If already connected

**Example:**

```python
await client._connect(update_tools=True)
tools = client.get_tools()
```

### `_format_tools_for_openai() -> list[ToolFunctionSchema]`

Converts MCP tool schemas to OpenAI-compatible format.

**Returns:**

- `list[ToolFunctionSchema]`: List of tools in OpenAI format

**Note:** This is an internal method used during connection.

### `_cast_tool_to_amrita() -> None`

Caches the OpenAI-format tools internally.

**Note:** Internal method called automatically after connection.

### `get_tools() -> list[ToolFunctionSchema]`

Retrieves the list of tools in OpenAI-compatible format.

**Returns:**

- `list[ToolFunctionSchema]`: List of available tools

**Example:**

```python
tools = client.get_tools()
for tool in tools:
    print(f"Tool: {tool.function.name} - {tool.function.description}")
```

### `get_original_tools() -> list[MCPToolSchema]`

Retrieves the original MCP tool schemas.

**Returns:**

- `list[MCPToolSchema]`: Original MCP tools from the server

**Example:**

```python
original_tools = client.get_original_tools()
for tool in original_tools:
    print(f"MCP Tool: {tool.name}")
```

### `async _close() -> None`

Closes the connection to the MCP server.

**Note:** Automatically called when exiting async context manager.

## Complete Usage Example

```python
import asyncio
from amrita_core.tools.mcp import MCPClient


async def main():
    # Method 1: Using context manager (recommended)
    async with MCPClient("/path/to/server.mcp") as client:
        # Get available tools
        tools = client.get_tools()
        print(f"Available tools: {[t.function.name for t in tools]}")

        # Call a tool
        result = await client.simple_call("calculate", {"expression": "2 + 2"})
        print(f"Result: {result}")

    # Method 2: Manual connection management
    client = MCPClient("/another/server.mcp")
    try:
        await client._connect(update_tools=True)
        tools = client.get_tools()
        result = await client.simple_call("search", {"query": "test"})
    finally:
        await client._close()


asyncio.run(main())
```

## Error Handling

MCPClient includes built-in error handling:

- **Connection errors**: Raised as exceptions during `_connect()`
- **Tool execution errors**: Returns JSON error response instead of raising
- **Automatic cleanup**: Connection always closed in `finally` block or context manager

## Related Documentation

- [ClientManager](ClientManager.md) - Multi-client management
- [MCP Server Integration](../../guide/extensions-integration/mcp-server-integration.md) - Detailed integration guide
- [ToolsManager](ToolsManager.md) - Tool registration and management
