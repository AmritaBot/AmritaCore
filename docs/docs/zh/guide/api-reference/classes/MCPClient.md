# MCPClient

MCPClient 类提供可复用的客户端，用于连接和交互 MCP 服务器。

## 概述

MCPClient 处理单个 MCP 服务器连接、工具发现、格式转换和工具执行。它作为 AmritaCore
工具系统与外部 MCP 兼容服务之间的桥梁。

## 属性

- `mcp_client` (Client | None)：底层的 FastMCP 客户端实例
- `server_script` (str | Path)：MCP 服务器脚本路径或 URI
- `tools` (list[MCPToolSchema])：从服务器获取的原始 MCP 工具列表
- `openai_tools` (list[ToolFunctionSchema])：转换为 OpenAI 兼容格式的工具列表

## 方法

### `__init__(server_script: str | Path) -> None`

初始化特定服务器的 MCP 客户端。

**参数：**

- `server_script`：MCP 服务器脚本路径或 URI

**示例：**

```python
from amrita_core.tools.mcp import MCPClient

client = MCPClient("/path/to/weather-server.mcp")
```

### `async __aenter__() -> Self`

异步上下文管理器入口——连接到 MCP 服务器。

**返回：**

- `Self`：客户端实例，便于链式调用

**示例：**

```python
async with MCPClient("/path/to/server.mcp") as client:
    tools = client.get_tools()
```

### `async __aexit__(exc_type, exc_val, exc_tb) -> None`

异步上下文管理器出口——关闭连接。

### `async simple_call(tool_name: str, data: dict[str, Any]) -> str`

调用 MCP 工具并返回结果。

**参数：**

- `tool_name`：要调用的工具名
- `data`：工具参数字典

**返回：**

- `str`：工具执行结果（文本内容）
- 出错时：带错误详情的 JSON 字符串 `{"success": False, "error": "..."}`

**示例：**

```python
result = await client.simple_call("get_weather", {"city": "New York"})
print(result)  # "Weather in New York: Sunny, 25°C"
```

### `async _connect(update_tools: bool = False) -> None`

与 MCP 服务器建立连接。

**参数：**

- `update_tools`：为 True 时获取并转换可用工具

**抛出：**

- `RuntimeError`：已连接时

**示例：**

```python
await client._connect(update_tools=True)
tools = client.get_tools()
```

### `_format_tools_for_openai() -> list[ToolFunctionSchema]`

把 MCP 工具 schema 转换为 OpenAI 兼容格式。

**返回：**

- `list[ToolFunctionSchema]`：OpenAI 格式的工具列表

**注意：** 这是连接期间使用的内部方法。

### `_cast_tool_to_amrita() -> None`

在内部缓存 OpenAI 格式的工具。

**注意：** 连接后自动调用的内部方法。

### `get_tools() -> list[ToolFunctionSchema]`

获取 OpenAI 兼容格式的工具列表。

**返回：**

- `list[ToolFunctionSchema]`：可用工具列表

**示例：**

```python
tools = client.get_tools()
for tool in tools:
    print(f"Tool: {tool.function.name} - {tool.function.description}")
```

### `get_original_tools() -> list[MCPToolSchema]`

获取原始的 MCP 工具 schema。

**返回：**

- `list[MCPToolSchema]`：来自服务器的原始 MCP 工具

**示例：**

```python
original_tools = client.get_original_tools()
for tool in original_tools:
    print(f"MCP Tool: {tool.name}")
```

### `async _close() -> None`

关闭与 MCP 服务器的连接。

**注意：** 退出异步上下文管理器时自动调用。

## 完整使用示例

```python
import asyncio
from amrita_core.tools.mcp import MCPClient


async def main():
    # 方式一：使用上下文管理器（推荐）
    async with MCPClient("/path/to/server.mcp") as client:
        # 获取可用工具
        tools = client.get_tools()
        print(f"Available tools: {[t.function.name for t in tools]}")

        # 调用工具
        result = await client.simple_call("calculate", {"expression": "2 + 2"})
        print(f"Result: {result}")

    # 方式二：手动管理连接
    client = MCPClient("/another/server.mcp")
    try:
        await client._connect(update_tools=True)
        tools = client.get_tools()
        result = await client.simple_call("search", {"query": "test"})
    finally:
        await client._close()


asyncio.run(main())
```

## 错误处理

MCPClient 内置错误处理：

- **连接错误**：在 `_connect()` 期间作为异常抛出
- **工具执行错误**：返回 JSON 错误响应，而不是抛出异常
- **自动清理**：连接始终在 `finally` 块或上下文管理器中关闭

## 相关文档

- [ClientManager](ClientManager.md) - 多客户端管理
- [MCP 服务器集成](../../extensions-integration/mcp-server.md) - 详细的集成指南
- `ToolsManager` - 工具注册与管理
