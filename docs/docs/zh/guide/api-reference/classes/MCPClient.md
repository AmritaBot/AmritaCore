# MCPClient

MCPClient 类提供了一个可复用的客户端，用于连接和使用 MCP（Model Context Protocol）服务器。

## 概述

MCPClient 处理单个 MCP 服务器的连接、工具发现、格式转换和工具执行。它作为 AmritaCore 工具系统与外部兼容 MCP 的服务之间的桥梁。

## 属性

- `mcp_client` (Client | None): 底层的 FastMCP 客户端实例
- `server_script` (str | Path): MCP 服务器脚本路径或 URI
- `tools` (list[MCPToolSchema]): 从服务器获取的原始 MCP 工具列表
- `openai_tools` (list[ToolFunctionSchema]): 转换为 OpenAI 兼容格式的工具列表

## 方法

### `__init__(server_script: str | Path) -> None`

为特定服务器初始化 MCP 客户端。

**参数：**

- `server_script`: MCP 服务器脚本的路径或 URI

**示例：**

```python
from amrita_core.tools.mcp import MCPClient

client = MCPClient("/path/to/weather-server.mcp")
```

### `async __aenter__() -> Self`

异步上下文管理器入口 - 连接到 MCP 服务器。

**返回值：**

- `Self`: 客户端实例，用于方法链式调用

**示例：**

```python
async with MCPClient("/path/to/server.mcp") as client:
    tools = client.get_tools()
```

### `async __aexit__(exc_type, exc_val, exc_tb) -> None`

异步上下文管理器出口 - 关闭连接。

### `async simple_call(tool_name: str, data: dict[str, Any]) -> str`

调用 MCP 工具并返回结果。

**参数：**

- `tool_name`: 要调用的工具名称
- `data`: 工具参数字典

**返回值：**

- `str`: 工具执行结果（文本内容）
- 出错时：返回 JSON 错误响应 `{"success": False, "error": "..."}`

**示例：**

```python
result = await client.simple_call("get_weather", {"city": "New York"})
print(result)  # "Weather in New York: Sunny, 25°C"
```

### `async _connect(update_tools: bool = False) -> None`

建立与 MCP 服务器的连接。

**参数：**

- `update_tools`: 如果为 True，获取并转换可用工具

**异常：**

- `RuntimeError`: 如果已经连接

**示例：**

```python
await client._connect(update_tools=True)
tools = client.get_tools()
```

### `_format_tools_for_openai() -> list[ToolFunctionSchema]`

将 MCP 工具模式转换为 OpenAI 兼容格式。

**返回值：**

- `list[ToolFunctionSchema]`: OpenAI 格式的工具列表

**注意：** 这是内部方法，在连接期间自动使用。

### `_cast_tool_to_amrita() -> None`

在内部缓存 OpenAI 格式的工具。

**注意：** 内部方法，连接后自动调用。

### `get_tools() -> list[ToolFunctionSchema]`

获取 OpenAI 兼容格式的工具列表。

**返回值：**

- `list[ToolFunctionSchema]`: 可用工具列表

**示例：**

```python
tools = client.get_tools()
for tool in tools:
    print(f"工具：{tool.function.name} - {tool.function.description}")
```

### `get_original_tools() -> list[MCPToolSchema]`

获取原始 MCP 工具模式。

**返回值：**

- `list[MCPToolSchema]`: 来自服务器的原始 MCP 工具

**示例：**

```python
original_tools = client.get_original_tools()
for tool in original_tools:
    print(f"MCP 工具：{tool.name}")
```

### `async _close() -> None`

关闭与 MCP 服务器的连接。

**注意：** 退出异步上下文管理器时自动调用。

## 完整使用示例

```python
import asyncio
from amrita_core.tools.mcp import MCPClient

async def main():
    # 方法 1：使用上下文管理器（推荐）
    async with MCPClient("/path/to/server.mcp") as client:
        # 获取可用工具
        tools = client.get_tools()
        print(f"可用工具：{[t.function.name for t in tools]}")

        # 调用工具
        result = await client.simple_call(
            "calculate",
            {"expression": "2 + 2"}
        )
        print(f"结果：{result}")

    # 方法 2：手动连接管理
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

MCPClient 包含内置错误处理：

- **连接错误**: 在 `_connect()` 期间作为异常抛出
- **工具执行错误**: 返回 JSON 错误响应而不是抛出异常
- **自动清理**: 在 `finally` 块或上下文管理器中始终关闭连接

## 相关文档

- [ClientManager](ClientManager.md) - 多客户端管理
- [MCP 服务集成](../../guide/extensions-integration/mcp-server-integration.md) - 详细集成指南
- [ToolsManager](ToolsManager.md) - 工具注册和管理
