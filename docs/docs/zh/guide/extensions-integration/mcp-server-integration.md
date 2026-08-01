# MCP 服务器集成

## 理解 AmritaCore 的 MCP 架构

**重要：** AmritaCore 将 MCP 作为**消费者/客户端**集成，而非作为 MCP 服务器提供者。这意味着：

- ✅ **内置**：AmritaCore 可以连接并使用 MCP 服务器（外部工具/服务）
- ❌ **非内置**：AmritaCore 不原生向外部消费者提供 MCP 服务
- 🔧 **需要自定义实现**：如果你需要将 AmritaCore 功能作为 MCP 服务器暴露，你需要自行实现 MCP 服务器协议

## MCP 如何在 AmritaCore 中工作

AmritaCore 的 MCP 集成通过**包装 MCP 服务器并将其注入工具管理器**来工作。架构如下：

```mermaid
graph TD
    A[AmritaCore Agent] --> B[ToolsManager]
    B --> C[MCP 客户端管理器]
    C --> D[MCP 服务器 1<br/>天气服务]
    C --> E[MCP 服务器 2<br/>数据库]
    C --> F[MCP 服务器 3<br/>日历 API]
    B --> G[原生工具<br/>simple_tool/on_tools]
```

**工作流程：**

1. **连接**：`ClientManager` 通过脚本建立到 MCP 服务器的连接
2. **工具发现**：从每个 MCP 服务器获取可用工具
3. **格式转换**：将 MCP 工具 schema 转换为 OpenAI 兼容格式
4. **注册**：将 MCP 工具作为可调用函数注册到 `ToolsManager` 中
5. **执行**：当 agent 调用工具时，`MCPClient` 调用远程 MCP 服务器并返回结果

## 核心组件

### MCPClient

[`MCPClient`](../api-reference/classes/MCPClient.md) 类处理单个 MCP 服务器连接：

```python
from amrita_core.tools.mcp import MCPClient

# 为特定的 MCP 服务器创建客户端
client = MCPClient(server_script="/path/to/server.mcp")

# 连接并获取工具
async with client:
    tools = client.get_tools()  # 获取 OpenAI 格式的工具
    original_tools = client.get_original_tools()  # 获取原始 MCP 工具

    # 直接调用工具
    result = await client.simple_call("tool_name", {"param": "value"})
```

### ClientManager / MultiClientManager

[`ClientManager`](../api-reference/classes/ClientManager.md)（单例）管理多个 MCP 客户端：

```python
from amrita_core.tools.mcp import ClientManager

# 初始化管理器
manager = ClientManager()

# 注册并初始化多个服务器
scripts = [
    "/path/to/weather.mcp",
    "/path/to/database.mcp"
]
await manager.initialize_scripts_all(scripts)

# 通过工具名获取客户端（处理路由）
client = await manager.get_client_by_tool_name("get_weather")
```

**关键特性：**

- **自动工具注册**：注册服务器的所有工具自动添加到 `ToolsManager`
- **工具名冲突解决**：重复的工具名自动重新映射（例如 `referred_42_search`）
- **客户端路由**：自动将工具调用路由到正确的 MCP 服务器
- **生命周期管理**：处理多个服务器的连接/断开

## 基于配置的设置

推荐方法是通过 [`AmritaConfig`](../api-reference/classes/AmritaConfig.md) 配置 MCP 服务器：

```python
from amrita_core import create_agent, minimal_init
from amrita_core.config import AmritaConfig, FunctionConfig

# 配置 MCP 服务器
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

# 使用配置初始化
await minimal_init(config)

# 创建 agent——MCP 工具自动可用
agent = create_agent(
    base_url="https://api.example.com",
    api_key="your-api-key",
    model="gpt-4"
)
```

## 手动客户端管理

对于需要动态 MCP 服务器管理的高级场景：

```python
import asyncio
from amrita_core.tools.mcp import ClientManager, MCPClient

async def manual_mcp_setup():
    # 初始化管理器
    manager = ClientManager()

    # 选项 1：通过服务器脚本注册
    manager.register_only(server_script="/path/to/server.mcp")

    # 选项 2：注册预创建的客户端
    custom_client = MCPClient("/another/path.mcp")
    manager.register_only(client=custom_client)

    # 初始化所有已注册的服务器
    await manager.initialize_all()

    # 获取可用工具
    available_tools = manager.tools_manager.get_tools()
    print(f"可用工具：{list(available_tools.keys())}")

    # 稍后动态添加新服务器
    await manager.initialize_this("/dynamic/new-server.mcp")

    # 移除服务器
    await manager.unregister_client("/path/to/remove.mcp")
```

## 工具执行流程

当 agent 调用 MCP 工具时：

```python
# Agent 决定调用工具
# LLM 生成：{ "tool_calls": [{"name": "get_weather", "arguments": {"city": "NYC"}}] }

# 框架路由到 MCP 客户端
# ClientManager.get_client_by_tool_name("get_weather") 找到正确的客户端

# MCP 客户端调用远程服务器
result = await mcp_client.simple_call("get_weather", {"city": "NYC"})

# 服务器处理并返回
# MCP 服务器执行：get_weather(city="NYC")
# 返回："纽约天气：晴，25°C"

# 结果发送回 LLM
# 工具响应追加到消息中
# LLM 使用工具输出生成最终响应
```

## 错误处理

MCP 集成包含强大的错误处理：

```python
from amrita_core.tools.mcp import MCPClient

client = MCPClient("/path/to/server.mcp")

try:
    async with client:
        result = await client.simple_call("tool_name", {"param": "value"})
        # 成功时：返回字符串结果
        # 失败时：返回带有错误详情的 JSON
        # {"success": False, "error": "详细错误信息"}
except Exception as e:
    # 连接错误、初始化失败
    print(f"MCP 操作失败：{e}")
```

**处理的错误场景：**

- 服务器脚本未找到 → 记录错误，继续处理其他服务器
- 工具执行失败 → 向 LLM 返回结构化错误 JSON
- 连接超时 → 下次调用时自动重试
- 重复的工具名称 → 自动重新映射并记录警告日志

## 传输 URL 格式

AmritaCore 支持灵活的基于 URL 的格式来指定 MCP 服务器传输方式。除了本地 `.py`/`.js` 脚本文件外，你可以使用 URL 方案连接到远程或基于 stdio 的服务器：

### `extra+protocol` 模式（通用）

```
EXTRA+PROTOCOL://[user:pwd@]host[:port]/path
```

`EXTRA` 部分映射到在 AmritaCore 中注册的传输类型：

| Extra        | 传输                  | 示例                              |
| ------------ | --------------------- | --------------------------------- |
| `sse`        | 服务器发送事件（SSE） | `sse+http://127.0.0.1:9178/sse`   |
| `streamable` | 可流式 HTTP           | `streamable+http://localhost/mcp` |

### 简写方案

为方便起见，常见传输有简写形式：

| 简写     | 展开为        | 示例                       |
| -------- | ------------- | -------------------------- |
| `sse://` | `sse+http://` | `sse://127.0.0.1:9178/sse` |

### 认证

直接在 URL 中包含凭据用于 `sse` 传输：

```
sse+http://admin:secret@host:8080/sse   # BasicAuth
sse+http://token@host/sse               # BearerAuth（仅用户名）
sse://user:pwd@host/sse                 # 简写带 BasicAuth
```

### `stdio://` — 基于命令行

使用 JSON 数组语法指定命令和参数：

```
stdio://["uvx","mcp-server-git"]
stdio://["npx","-y","@modelcontextprotocol/server-everything"]
stdio://["python","my_mcp_server.py","--port","8080"]
```

### 普通 `http(s)://`

标准 HTTP/HTTPS URL 直接传递到 MCP 传输层：

```
http://example.com/mcp
https://mcp-server.internal/sse
```

### 本地脚本文件

本地 `.py` 和 `.js` 文件继续像以前一样工作：

```
./mcp-scripts/weather.py
/tmp/my_server.js
```

### 配置示例

```python
from amrita_core.config import AmritaConfig, FunctionConfig

# 混合使用不同的传输类型
config = AmritaConfig(
    function_config=FunctionConfig(
        agent_mcp_client_enable=True,
        agent_mcp_server_scripts=[
            "sse+http://localhost:9178/sse",               # 远程 SSE 服务器
            "sse+https://admin:pass@mcp.example.com/sse",  # 带认证的 SSE
            "streamable+http://mcp.internal/",             # 可流式 HTTP
            'stdio://["uvx","mcp-server-git"]',            # Stdio 进程
            "./mcp-scripts/local-tool.py",                 # 本地脚本
        ]
    )
)
```

### 工作原理

`amrita_core.tools._parser` 中的 [`resolve_transport`](../api-reference/classes/MCPClient.md) 函数自动检测 URL 方案并创建适当的 `fastmcp` 传输。所有格式都可以在 `agent_mcp_server_scripts` 列表中自由混合。

## 创建自己的 MCP 服务器

由于 AmritaCore 不提供内置的 MCP 服务器功能，你需要创建自己的 MCP 服务器来暴露 AmritaCore 功能。以下是使用 MCP Python SDK 的最小示例：

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
            description="与 AmritaCore AI 助手聊天",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "发送给 AI 的消息"
                    }
                },
                "required": ["message"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "amrita_chat":
        # 在此处集成 AmritaCore
        response = "来自 AmritaCore 的问候！"  # 你的集成逻辑
        return [TextContent(type="text", text=response)]
    raise ValueError(f"未知工具：{name}")

async def main():
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

然后从 AmritaCore 连接到它：

```python
from amrita_core.config import AmritaConfig, FunctionConfig

config = AmritaConfig(
    function_config=FunctionConfig(
        agent_mcp_client_enable=True,
        agent_mcp_server_scripts=["./my_amrita_server.py"]
    )
)
```

## 最佳实践

### 性能优化

- 在应用生命周期早期初始化 MCP 服务器
- 重用 `ClientManager` 实例（它是单例）
- 避免频繁的连接/断开循环
- 使用 `initialize_all()` 进行批量初始化

### 安全考虑

- 验证 MCP 服务器脚本路径
- 为远程 MCP 服务器实施认证
- 在发送到 MCP 服务器之前清理工具输入
- 监控工具执行时间和资源使用

### 开发技巧

- 在集成前独立测试 MCP 服务器
- 使用描述性工具名称以避免冲突
- 在 MCP 服务器中实现适当的错误处理
- 记录工具调用以便调试

## 相关文档

- [扩展与集成索引](./index.md) - 所有扩展机制的概述
- [`ClientManager` API 参考](../api-reference/classes/ClientManager.md) - 完整的 API 文档

## 新的 MCP 客户端绑定方法

AmritaCore 提供了一种简化的方法，使用 `bound_to()` 方法将 MCP 客户端直接绑定到客户端管理器。

### 使用 bound_to() 方法

[`bound_to()`](../api-reference/classes/MCPClient.md#bound_to) 方法提供了一种更直接、更受控的方式来注册 MCP 客户端：

```python
from amrita_core.tools.mcp import MCPClient, ClientManager

async def setup_mcp_client():
    # 创建 MCP 客户端
    client = MCPClient(server_script="/path/to/weather.mcp")

    # 获取全局客户端管理器
    manager = ClientManager()

    # 将客户端直接绑定到管理器
    await client.bound_to(manager)

    print("MCP 客户端成功绑定到管理器！")
```

**`bound_to()` 的优势：**

- **原子操作**：绑定操作是原子的 — 完全成功或在失败时完全回滚
- **错误安全**：如果注册失败，客户端会自动取消注册以防止部分状态
- **直接控制**：提供对客户端注册的显式控制，无需通过脚本初始化

### 对比：传统方式 vs 新方式

| 特性         | 传统方式（`initialize_scripts_all`） | 新方式（`bound_to`） |
| ------------ | ------------------------------------ | -------------------- |
| **用例**     | 从配置/脚本批量初始化                | 直接客户端绑定       |
| **控制级别** | 高级，配置驱动                       | 低级，编程式         |
| **错误处理** | 每个脚本的错误处理                   | 失败时原子回滚       |
| **灵活性**   | 仅限于基于脚本的设置                 | 完全的编程式控制     |

### 带错误处理的完整示例

```python
import asyncio
from amrita_core.tools.mcp import MCPClient, ClientManager

async def robust_mcp_setup():
    client = MCPClient(server_script="./weather-service.mcp")
    manager = ClientManager()

    try:
        # 尝试绑定客户端
        await client.bound_to(manager)
        print("✅ MCP 客户端绑定成功")

        # 使用客户端
        tools = client.get_tools()
        print(f"可用工具：{[tool.function.name for tool in tools]}")

    except Exception as e:
        print(f"❌ 绑定 MCP 客户端失败：{e}")
        # 失败时客户端自动清理
        raise

# 运行示例
asyncio.run(robust_mcp_setup())
```

**注意**：`bound_to()` 方法在需要在运行时动态注册 MCP 客户端或实现自定义 MCP 客户端管理逻辑时特别有用。
