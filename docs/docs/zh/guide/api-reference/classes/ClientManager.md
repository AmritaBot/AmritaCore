# ClientManager

ClientManager 类为多个 MCP 服务器连接和工具注册提供集中管理。

## 概述

ClientManager 是一个**单例类，继承自 [`MultiClientManager`](MultiClientManager.md)**，继承其所有功能，同时添加了单例模式支持以实现全局可访问性。它管理多个 MCP 客户端，通过自动重映射解决工具名冲突，把工具调用路由到合适的服务器，并自动把所有发现的工具注册进 ToolsManager。

## 继承

```text
ClientManager → MultiClientManager
```

ClientManager 继承 MultiClientManager 的全部方法与属性，并新增：

- 通过 `__new__()` 实现的单例实例管理
- 全局单实例访问模式

## 属性

_继承自 [`MultiClientManager`](MultiClientManager.md)：_

- `clients` (list[MCPClient])：所有已注册 MCP 客户端的列表
- `script_to_clients` (dict[str, MCPClient])：服务器脚本路径到客户端的映射
- `name_to_clients` (dict[str, MCPClient])：工具名到其所属客户端的映射
- `tools_remapping` (dict[str, str])：工具名重映射（原始 → 重映射后）
- `reversed_remappings` (dict[str, str])：反向重映射（重映射后 → 原始）
- `tools_manager` (MultiToolsManager)：MCP 工具注册到的工具管理器
- `_is_initialized` (bool)：所有客户端是否已初始化

## 方法

### `__new__() -> Self`

创建或返回 ClientManager 的单例实例。

**返回：**

- `Self`：单例实例

**注意：** ClientManager 实现了单例模式——每个应用只存在一个实例。每次调用
`ClientManager()` 都返回同一个实例。

**示例：**

```python
from amrita_core.tools.mcp import ClientManager

manager1 = ClientManager()
manager2 = ClientManager()
print(manager1 is manager2)  # True - 同一个实例
```

### `__init__() -> None`

初始化 ClientManager（由于单例模式，只执行一次）。

**注意：** 初始化逻辑只在首次实例化时执行。

_其余所有方法均继承自 [`MultiClientManager`](MultiClientManager.md)：_

- `get_client_by_script(server_script)` - 按服务器脚本获取客户端
- `get_client_by_tool_name(tool_name)` - 查找拥有某个工具的客户端
- `register_only(client)` / `register_only(server_script)` - 仅注册，不初始化
- `initialize_this(server_script)` - 注册并初始化单个服务器
- `initialize_scripts_all(scripts)` - 初始化多个服务器
- `initialize_all()` - 连接所有已注册的服务器
- `update_tools(client)` - 从某个客户端更新工具
- `unregister_client(script_name)` - 移除某个服务器
- `reinitialize_all()` - 刷新所有连接

详细的方法说明见 [`MultiClientManager`](MultiClientManager.md) 文档。

## 完整使用示例

```python
import asyncio
from amrita_core.tools.mcp import ClientManager


async def main():
    # 获取单例实例
    manager = ClientManager()

    # 方式一：基于配置的设置（推荐）
    # 声明式配置见 AmritaConfig

    # 方式二：编程式设置
    scripts = ["/path/to/weather.mcp", "/path/to/database.mcp", "/path/to/calendar.mcp"]

    # 注册并初始化所有服务器
    await manager.initialize_scripts_all(scripts)

    # 查看可用工具
    available_tools = manager.tools_manager.get_tools()
    print(f"Available tools: {list(available_tools.keys())}")

    # 查找某个工具属于哪个客户端
    weather_client = await manager.get_client_by_tool_name("get_weather")
    print(f"Tool owner: {weather_client.server_script}")

    # 处理重复的工具名（自动重映射）
    # 若两个服务器都有 "search" 工具，第二个会变成 "referred_42_search"

    # 动态添加新服务器
    await manager.initialize_this("/dynamic/new-server.mcp")

    # 移除某个服务器
    await manager.unregister_client("/path/to/old-server.mcp")

    # 重新初始化全部（刷新连接）
    await manager.reinitialize_all()


asyncio.run(main())
```

## 关键特性

### 自动工具注册

来自已注册 MCP 服务器的所有工具都会自动加入 `ToolsManager`，并对 agent 可用。

### 工具名冲突解决

当多个服务器提供同名工具时：

- 首次注册保留原名
- 后续注册会被自动重映射（如 `referred_42_search`）
- 冲突会生成警告日志

### 智能路由

调用某个工具时，`ClientManager` 会依据工具名映射自动把请求路由到正确的 MCP 服务器。

### 线程安全

所有操作都由一把异步锁（`_lock`）保护，确保对共享状态的线程安全访问。

### 生命周期管理

同时处理多个服务器的连接建立、工具发现、注册与清理。

## 错误处理

- **服务器初始化失败**：记录错误并继续处理其他服务器（除非 `fail_then_raise=True`）
- **工具执行错误**：由各自的 `MCPClient` 处理，返回结构化的错误 JSON
- **重复工具**：自动重映射并输出警告日志
- **连接丢失**：在下次工具调用时自动重试

## 相关文档

- [MCPClient](MCPClient.md) - 单个客户端管理
- `ToolsManager` - 工具注册系统
- [MCP 服务器集成](../../extensions-integration/mcp-server.md) - 完整的集成指南
- [AmritaConfig](AmritaConfig.md) - 基于配置的设置
