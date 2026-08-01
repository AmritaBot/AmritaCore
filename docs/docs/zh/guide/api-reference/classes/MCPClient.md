# MCPClient

MCPClient 类提供可复用的客户端，用于连接和交互 MCP 服务器。

## 概述

MCPClient 处理单个 MCP 服务器连接、工具发现、格式转换和工具执行。它作为 AmritaCore 工具系统与外部 MCP 兼容服务之间的桥梁。

## 属性

- `mcp_client` (Client | None)：底层的 FastMCP 客户端实例
- `server_script` (str | Path)：MCP 服务器脚本路径或 URI
- `tools` (list[MCPToolSchema])：从服务器获取的原始 MCP 工具列表
- `openai_tools` (list[ToolFunctionSchema])：转换为 OpenAI 兼容格式的工具列表

## 方法

### `__init__(server_script: str | Path) -> None`

初始化特定服务器的 MCP 客户端。

```python
from amrita_core.tools.mcp import MCPClient

client = MCPClient("/path/to/weather-server.mcp")
```

### `async __aenter__() -> Self`

异步上下文管理器入口——连接到 MCP 服务器。

### `async __aexit__(exc_type, exc_val, exc_tb) -> None`

异步上下文管理器出口——关闭连接。

### `async simple_call(tool_name: str, data: dict[str, Any]) -> str`

调用 MCP 工具并返回结果。

```python
result = await client.simple_call("get_weather", {"city": "北京"})
```
