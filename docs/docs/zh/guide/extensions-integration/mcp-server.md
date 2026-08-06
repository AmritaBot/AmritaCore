# MCP 服务器

AmritaCore 内嵌 **Model Context Protocol 客户端**（`MCPClient` /
`MultiClientManager`），让任意 MCP 服务器成为工具来源。

## 服务器脚本格式

服务器脚本是 `str | Path`，支持：

- **文件路径** —— `"path/to/server.py"`（stdio 传输）
- **URL** —— `"https://mcp.example.com/sse"`、`"sse://..."`、
  `"stream+http(s)://..."`、`"stdio://..."`

## 标准用法：配置 + 加载

标准方式是**配置驱动**：在 `FunctionConfig` 里列出服务器，让
`minimal_init()` / `load_amrita()` 启动它们。

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
await minimal_init(config)  # 加载并初始化所有 MCP 客户端
```

之后每个 MCP 工具都像常规工具一样注册进全局工具管理器——agent 按名调用即可。

## 高级用法：直接驱动 `ClientManager`

`ClientManager` 是**单例**——`load_amrita()` 用的就是同一个实例。需要运行时
控制时自己驱动它：

```python
from amrita_core.tools.mcp import ClientManager

manager = ClientManager()  # 单例

# 一次性：注册 + 立即连接。
await manager.initialize_this("path/to/server.py")

# 或批量（单个失败不影响其余）。
await manager.initialize_scripts_all(
    [
        "path/to/server-a.py",
        "https://mcp.example.com/sse",
    ]
)

# 延迟：先注册，后连接（例如绑定到会话之后）。
manager.register_only(server_script="path/to/server-b.py")
await manager.initialize_all()
```

`ClientManager` 继承 `MultiClientManager`——后者把工具名映射到客户端、
重映射重复工具名，并暴露 `unregister_client(script)` / `reinitialize_all()` /
`update_tools(client)`。**会话隔离**：自行创建 `MultiClientManager` 实例，
通过 ability 上下文挂到不同会话（见[数据后端](../concepts/data-backend.md)）。

## 直接使用 `MCPClient`

单个服务器可直接用 `MCPClient`——适合测试或一次性集成：

```python
from amrita_core.tools.mcp import MCPClient, MultiClientManager

client = MCPClient("path/to/server.py", connection_ttl=120)  # 空闲 TTL 后关闭；-1 禁用

# 绑定到管理器（注册 + 加载工具）。
await client.bound_to(MultiClientManager())

# 或绕过 agent 直接调用工具。
result = await client.simple_call("list_files", {"path": "/tmp"})
```

`connection_ttl` 控制空闲关闭：`ttl` 秒未使用后连接关闭，下次调用自动重连。
`-1` 保持常开。

## 下一步

[自定义 Tokenizer](tokenizer.md)——接入自己的 tokenizer 用于用量统计。
