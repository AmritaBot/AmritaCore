# MCP Server Integration

## Understanding AmritaCore's MCP Architecture

**Important:** AmritaCore integrates MCP as a **consumer/client**, not as an MCP server provider. This means:

- ✅ **Built-in**: AmritaCore can connect to and consume MCP servers (external tools/services)
- ❌ **Not Built-in**: AmritaCore does not natively provide MCP services to external consumers
- 🔧 **Custom Implementation Required**: If you need to expose AmritaCore functionality as an MCP server, you'll need to implement the MCP server protocol yourself

## How MCP Works in AmritaCore

AmritaCore's MCP integration works by **wrapping MCP servers and injecting them into the tool manager**. Here's the architecture:

```mermaid
graph TD
    A[AmritaCore Agent] --> B[ToolsManager]
    B --> C[MCP Client Manager]
    C --> D[MCP Server 1<br/>Weather Service]
    C --> E[MCP Server 2<br/>Database]
    C --> F[MCP Server 3<br/>Calendar API]
    B --> G[Native Tools<br/>simple_tool/on_tools]
```

**Workflow:**

1. **Connection**: `ClientManager` establishes connections to MCP servers via scripts
2. **Tool Discovery**: Fetches available tools from each MCP server
3. **Format Conversion**: Converts MCP tool schemas to OpenAI-compatible format
4. **Registration**: Registers MCP tools into `ToolsManager` as callable functions
5. **Execution**: When agent calls a tool, `MCPClient` invokes the remote MCP server and returns results

## Core Components

### MCPClient

The [`MCPClient`](../api-reference/classes/MCPClient.md) class handles individual MCP server connections:

```python
from amrita_core.tools.mcp import MCPClient

# Create client for specific MCP server
client = MCPClient(server_script="/path/to/server.mcp")

# Connect and fetch tools
async with client:
    tools = client.get_tools()  # Get OpenAI-format tools
    original_tools = client.get_original_tools()  # Get raw MCP tools

    # Call a tool directly
    result = await client.simple_call("tool_name", {"param": "value"})
```

### ClientManager / MultiClientManager

The [`ClientManager`](../api-reference/classes/ClientManager.md) (singleton) manages multiple MCP clients:

```python
from amrita_core.tools.mcp import ClientManager

# Initialize manager
manager = ClientManager()

# Register and initialize multiple servers
scripts = [
    "/path/to/weather.mcp",
    "/path/to/database.mcp"
]
await manager.initialize_scripts_all(scripts)

# Get client by tool name (handles routing)
client = await manager.get_client_by_tool_name("get_weather")

# Update tools from specific client
await manager.update_tools(existing_client)
```

**Key Features:**

- **Automatic Tool Registration**: All tools from registered servers are automatically added to `ToolsManager`
- **Tool Name Conflict Resolution**: Duplicate tool names are automatically remapped (e.g., `referred_42_search`)
- **Client Routing**: Automatically routes tool calls to correct MCP server
- **Lifecycle Management**: Handles connection/disconnection of multiple servers

## Configuration-Based Setup

The recommended approach is to configure MCP servers via [`AmritaConfig`](../api-reference/classes/AmritaConfig.md):

```python
from amrita_core import create_agent, minimal_init
from amrita_core.config import AmritaConfig, FunctionConfig

# Configure MCP servers
config = AmritaConfig(
    function_config=FunctionConfig(
        agent_mcp_client_enable=True,
        agent_mcp_server_scripts=[
            "./mcp-scripts/weather.mcp",
            "./mcp-scripts/database.mcp",
            "./mcp-scripts/calendar.mcp"
        ]
    )
)

# Initialize with config
await minimal_init(config)

# Create agent - MCP tools are automatically available
agent = create_agent(
    base_url="https://api.example.com",
    api_key="your-api-key",
    model="gpt-4"
)
```

## Manual Client Management

For advanced scenarios requiring dynamic MCP server management:

```python
import asyncio
from amrita_core.tools.mcp import ClientManager, MCPClient

async def manual_mcp_setup():
    # Initialize manager
    manager = ClientManager()

    # Option 1: Register via server script
    manager.register_only(server_script="/path/to/server.mcp")

    # Option 2: Register pre-created client
    custom_client = MCPClient("/another/path.mcp")
    manager.register_only(client=custom_client)

    # Initialize all registered servers
    await manager.initialize_all()

    # Get available tools
    available_tools = manager.tools_manager.get_tools()
    print(f"Available tools: {list(available_tools.keys())}")

    # Dynamically add new server later
    await manager.initialize_this("/dynamic/new-server.mcp")

    # Remove a server
    await manager.unregister_client("/path/to/remove.mcp")
```

## Tool Execution Flow

When the agent calls an MCP tool:

```python
# 1. Agent decides to call tool
# LLM generates: { "tool_calls": [{"name": "get_weather", "arguments": {"city": "NYC"}}] }

# 2. Framework routes to MCP client
# ClientManager.get_client_by_tool_name("get_weather") finds correct client

# 3. MCP client calls remote server
result = await mcp_client.simple_call("get_weather", {"city": "NYC"})

# 4. Server processes and returns
# MCP server executes: get_weather(city="NYC")
# Returns: "Weather in NYC: Sunny, 25°C"

# 5. Result sent back to LLM
# Tool response appended to messages
# LLM generates final response using tool output
```

## Error Handling

MCP integration includes robust error handling:

```python
from amrita_core.tools.mcp import MCPClient

client = MCPClient("/path/to/server.mcp")

try:
    async with client:
        result = await client.simple_call("tool_name", {"param": "value"})
        # On success: returns string result
        # On failure: returns JSON with error details
        # {"success": False, "error": "Detailed error message"}
except Exception as e:
    # Connection errors, initialization failures
    print(f"MCP operation failed: {e}")
```

**Error Scenarios Handled:**

- Server script not found → Logs error, continues with other servers
- Tool execution fails → Returns structured error JSON to LLM
- Connection timeout → Automatic retry on next call
- Duplicate tool names → Auto-remapping with warning logs

## Transport URL Format

AmritaCore supports a flexible URL-based format for specifying MCP server transports. Instead of only local script `.py`/`.js` files, you can use URL schemes to connect to remote or stdio-based servers:

### `extra+protocol` Pattern (General)

```
EXTRA+PROTOCOL://[user:pwd@]host[:port]/path
```

The `EXTRA` portion maps to a transport type registered in AmritaCore:

| Extra        | Transport                | Example                           |
| ------------ | ------------------------ | --------------------------------- |
| `sse`        | Server-Sent Events (SSE) | `sse+http://127.0.0.1:9178/sse`   |
| `streamable` | Streamable HTTP          | `streamable+http://localhost/mcp` |

### Shorthand Schemes

For convenience, common transports have shorthand forms:

| Shorthand | Expands To    | Example                    |
| --------- | ------------- | -------------------------- |
| `sse://`  | `sse+http://` | `sse://127.0.0.1:9178/sse` |

### Authentication

Include credentials directly in the URL for `sse` transport:

```
sse+http://admin:secret@host:8080/sse   # BasicAuth
sse+http://token@host/sse               # BearerAuth (username-only)
sse://user:pwd@host/sse                 # Shorthand with BasicAuth
```

### `stdio://` — Command-Line Based

Use JSON array syntax to specify the command and arguments:

```
stdio://["uvx","mcp-server-git"]
stdio://["npx","-y","@modelcontextprotocol/server-everything"]
stdio://["python","my_mcp_server.py","--port","8080"]
```

### Plain `http(s)://`

Standard HTTP/HTTPS URLs are passed directly to the MCP transport layer:

```
http://example.com/mcp
https://mcp-server.internal/sse
```

### Local Script Files

Local `.py` and `.js` files continue to work as before:

```
./mcp-scripts/weather.py
/tmp/my_server.js
```

### Configuration Examples

```python
from amrita_core.config import AmritaConfig, FunctionConfig

# Mix and match transport types
config = AmritaConfig(
    function_config=FunctionConfig(
        agent_mcp_client_enable=True,
        agent_mcp_server_scripts=[
            "sse+http://localhost:9178/sse",               # Remote SSE server
            "sse+https://admin:pass@mcp.example.com/sse",  # SSE with auth
            "streamable+http://mcp.internal/",             # Streamable HTTP
            'stdio://["uvx","mcp-server-git"]',            # Stdio process
            "./mcp-scripts/local-tool.py",                 # Local script
        ]
    )
)
```

### How It Works

The [`resolve_transport`](../api-reference/classes/MCPClient.md) function in `amrita_core.tools._parser` automatically detects the URL scheme and creates the appropriate `fastmcp` transport. All formats can be freely mixed in your `agent_mcp_server_scripts` list.

## Creating Your Own MCP Server

Since AmritaCore doesn't provide built-in MCP server capabilities, you'll need to create your own MCP server to expose AmritaCore functionality. Here's a minimal example using the MCP Python SDK:

```python
# my_amrita_server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("amrita-tools")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="amrita_chat",
            description="Chat with AmritaCore AI assistant",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to send to AI"
                    }
                },
                "required": ["message"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "amrita_chat":
        # Integrate with AmritaCore here
        response = "Hello from AmritaCore!"  # Your integration logic
        return [TextContent(type="text", text=response)]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

Then connect to it from AmritaCore:

```python
from amrita_core.config import AmritaConfig, FunctionConfig

config = AmritaConfig(
    function_config=FunctionConfig(
        agent_mcp_client_enable=True,
        agent_mcp_server_scripts=["./my_amrita_server.py"]
    )
)
```

## Best Practices

### Performance Optimization

- Initialize MCP servers early in application lifecycle
- Reuse `ClientManager` instances (it's a singleton)
- Avoid frequent connect/disconnect cycles
- Use `initialize_all()` for batch initialization

### Security Considerations

- Validate MCP server script paths
- Implement authentication for remote MCP servers
- Sanitize tool inputs before sending to MCP servers
- Monitor tool execution time and resource usage

### Development Tips

- Test MCP servers independently before integration
- Use descriptive tool names to avoid conflicts
- Implement proper error handling in MCP servers
- Log tool invocations for debugging

## Related Documentation

- [Extensions and Integration Index](./index.md) - Overview of all extension mechanisms

- [`ClientManager` API Reference](../api-reference/classes/ClientManager.md) - Complete API documentation

## New MCP Client Binding Method

AmritaCore provides a simplified method to bind MCP clients directly to the client manager using the `bound_to()` method.

### Using bound_to() Method

The [`bound_to()`](../api-reference/classes/MCPClient.md#bound_to) method provides a more direct and controlled way to register MCP clients:

```python
from amrita_core.tools.mcp import MCPClient, ClientManager

async def setup_mcp_client():
    # Create MCP client
    client = MCPClient(server_script="/path/to/weather.mcp")

    # Get the global client manager
    manager = ClientManager()

    # Bind client directly to manager
    await client.bound_to(manager)

    print("MCP client successfully bound to manager!")
```

**Advantages of `bound_to()`:**

- **Atomic Operation**: The binding operation is atomic - either fully succeeds or fully rolls back on failure
- **Error Safety**: If registration fails, the client is automatically unregistered to prevent partial state
- **Direct Control**: Provides explicit control over client registration without going through script initialization

### Comparison: Traditional vs New Approach

| Feature            | Traditional (`initialize_scripts_all`)  | New (`bound_to`)           |
| ------------------ | --------------------------------------- | -------------------------- |
| **Use Case**       | Bulk initialization from config/scripts | Direct client binding      |
| **Control Level**  | High-level, configuration-driven        | Low-level, programmatic    |
| **Error Handling** | Per-script error handling               | Atomic rollback on failure |
| **Flexibility**    | Limited to script-based setup           | Full programmatic control  |

### Complete Example with Error Handling

```python
import asyncio
from amrita_core.tools.mcp import MCPClient, ClientManager

async def robust_mcp_setup():
    client = MCP_client(server_script="./weather-service.mcp")
    manager = ClientManager()

    try:
        # Attempt to bind client
        await client.bound_to(manager)
        print("✅ MCP client bound successfully")

        # Use the client
        tools = client.get_tools()
        print(f"Available tools: {[tool.function.name for tool in tools]}")

    except Exception as e:
        print(f"❌ Failed to bind MCP client: {e}")
        # Client is automatically cleaned up on failure
        raise

# Run the example
asyncio.run(robust_mcp_setup())
```

**Note**: The `bound_to()` method is particularly useful when you need to dynamically register MCP clients at runtime or when implementing custom MCP client management logic.
