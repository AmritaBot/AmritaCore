# MCP Servers

AmritaCore embeds a **Model Context Protocol client** (`MCPClient` /
`MultiClientManager`) so any MCP server becomes a tool source.

## Server Script Formats

A server script is `str | Path`, supporting:

- **File paths** — `"path/to/server.py"` (stdio transport)
- **URLs** — `"https://mcp.example.com/sse"`, `"sse://..."`,
  `"stream+http(s)://..."`, `"stdio://..."`

## Standard Usage: Configure, Then Load

The standard way is **configuration-driven**: list your servers in
`FunctionConfig` and let `minimal_init()` / `load_amrita()` start them.

```python
from amrita_core import minimal_init
from amrita_core.config import AmritaConfig, FunctionConfig

config = AmritaConfig(
    function_config=FunctionConfig(
        agent_mcp_client_enable=True,
        agent_mcp_server_scripts=[
            "path/to/filesystem-server.py",  # stdio
            "https://mcp.example.com/sse",  # HTTP/SSE
        ],
    )
)
await minimal_init(config)  # loads and initializes all MCP clients
```

After this, every MCP tool is registered in the global tools manager like a
regular tool — the agent can call them by name.

## Advanced Usage: `ClientManager` Directly

`ClientManager` is a **singleton** — the same instance is used by
`load_amrita()`. Drive it yourself for runtime control:

```python
from amrita_core.tools.mcp import ClientManager

manager = ClientManager()  # singleton

# One-shot: register + connect immediately.
await manager.initialize_this("path/to/server.py")

# Or in bulk (fails per-server without raising for the rest).
await manager.initialize_scripts_all(
    [
        "path/to/server-a.py",
        "https://mcp.example.com/sse",
    ]
)

# Deferred: register first, connect later (e.g. after binding to a session).
manager.register_only(server_script="path/to/server-b.py")
await manager.initialize_all()
```

`ClientManager` extends `MultiClientManager`, which maps tool names to their
client, remaps duplicate tool names, and exposes `unregister_client(script)` /
`reinitialize_all()` / `update_tools(client)`. For **per-session isolation**,
create your own `MultiClientManager` instances and attach them to sessions via
the ability context (see [Data Backend](../concepts/data-backend.md)).

## Direct `MCPClient` Usage

For a single server, use `MCPClient` directly — useful in tests or one-off
integrations:

```python
from amrita_core.tools.mcp import MCPClient, MultiClientManager

client = MCPClient(
    "path/to/server.py", connection_ttl=120
)  # TTL before idle close; -1 disables

# Bind to a manager (registers + loads tools).
await client.bound_to(MultiClientManager())

# Or call a tool directly without going through the agent.
result = await client.simple_call("list_files", {"path": "/tmp"})
```

`connection_ttl` controls idle-close: after `ttl` seconds of no use the
connection is closed; the next call reconnects. `-1` keeps it open.

## Tool Name Collisions

If an MCP tool name already exists in the tools manager, it is **remapped**
(`referred_<n>_<name>`) and the old tool is replaced — a warning is logged.
Use `get_client_by_tool_name(name)` to resolve a client from a (possibly
remapped) tool name.

## Next

[Custom Tokenizers](tokenizer.md) — plug your own tokenizer for usage accounting.
