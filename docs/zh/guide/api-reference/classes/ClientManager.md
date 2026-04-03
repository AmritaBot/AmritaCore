# ClientManager

ClientManager 类为多个 MCP（Model Context Protocol）服务器连接和工具注册提供集中管理。

## 概述

ClientManager 是一个**扩展自 [`MultiClientManager`](MultiClientManager.md) 的单例类**，继承了其所有功能，同时添加了单例模式支持以实现全局访问。它管理多个 MCP 客户端，通过自动重映射解决工具名称冲突，将工具调用路由到适当的服务器，并自动将所有发现的工具注册到 ToolsManager 中。

## 继承关系

```text
ClientManager → MultiClientManager
```

ClientManager 继承自 MultiClientManager 并添加了：

- 通过 `__new__()` 实现单例实例管理
- 全局单实例访问模式

## 属性

_继承自 [`MultiClientManager`](MultiClientManager.md)：_

- `clients` (list[MCPClient]): 所有已注册 MCP 客户端的列表
- `script_to_clients` (dict[str, MCPClient]): 从服务器脚本路径到客户端的映射
- `name_to_clients` (dict[str, MCPClient]): 从工具名称到其所属客户端的映射
- `tools_remapping` (dict[str, str]): 工具名称重映射（原始名称 → 重映射后的名称）
- `reversed_remappings` (dict[str, str]): 反向重映射（重映射后的名称 → 原始名称）
- `tools_manager` (MultiToolsManager): MCP 工具注册的工具管理器
- `_is_initialized` (bool): 是否所有客户端都已初始化

## 方法

### `__new__() -> Self`

创建或返回 ClientManager 的单例实例。

**返回值：**

- `Self`: 单例实例

**注意：** ClientManager 实现了单例模式 - 每个应用程序只有一个实例存在。每次调用 `ClientManager()` 都返回同一个实例。

**示例：**

```python
from amrita_core.tools.mcp import ClientManager

manager1 = ClientManager()
manager2 = ClientManager()
print(manager1 is manager2)  # True - 同一个实例
```

### `__init__() -> None`

初始化 ClientManager（由于单例模式，只运行一次）。

**注意：** 初始化逻辑仅在第一次实例化时执行。

---

_所有其他方法都继承自 [`MultiClientManager`](MultiClientManager.md)：_

- `get_client_by_script(server_script)` - 按服务器脚本获取客户端
- `get_client_by_tool_name(tool_name)` - 查找拥有特定工具的客户端
- `register_only(client)` / `register_only(server_script)` - 注册但不初始化
- `initialize_this(server_script)` - 注册并初始化单个服务器
- `initialize_scripts_all(scripts)` - 初始化多个服务器
- `initialize_all()` - 连接到所有已注册的服务器
- `update_tools(client)` - 更新客户端的工具
- `unregister_client(script_name)` - 移除服务器
- `reinitalize_all()` - 刷新所有连接

详细方法说明请参阅 [`MultiClientManager`](MultiClientManager.md) 文档。

## 完整使用示例

```python
import asyncio
from amrita_core.tools.mcp import ClientManager

async def main():
    # 获取单例实例
    manager = ClientManager()

    # 方法 1：基于配置的设置（推荐）
    # 参见 AmritaConfig 了解声明式配置

    # 方法 2：编程式设置
    scripts = [
        "/path/to/weather.mcp",
        "/path/to/database.mcp",
        "/path/to/calendar.mcp"
    ]

    # 注册并初始化所有服务器
    await manager.initialize_scripts_all(scripts)

    # 检查可用工具
    available_tools = manager.tools_manager.get_tools()
    print(f"可用工具：{list(available_tools.keys())}")

    # 查找哪个客户端拥有某个工具
    weather_client = await manager.get_client_by_tool_name("get_weather")
    print(f"工具所有者：{weather_client.server_script}")

    # 处理重复工具名称（自动重映射）
    # 如果两个服务器都有 "search" 工具，第二个会变成 "referred_42_search"

    # 动态添加新服务器
    await manager.initialize_this("/dynamic/new-server.mcp")

    # 移除服务器
    await manager.unregister_client("/path/to/old-server.mcp")

    # 重新初始化所有（刷新连接）
    await manager.reinitalize_all()

asyncio.run(main())
```

## 关键特性

### 自动工具注册

来自已注册 MCP 服务器的所有工具会自动添加到 `ToolsManager` 并对 Agent 可用。

### 工具名称冲突解决

当多个服务器提供相同名称的工具时：

- 第一次注册保留原始名称
- 后续注册会自动重映射（例如 `referred_42_search`）
- 生成警告日志记录冲突

### 智能路由

当调用工具时，`ClientManager` 根据工具名称映射自动将请求路由到正确的 MCP 服务器。

### 线程安全

所有操作都受异步锁（`_lock`）保护，确保对共享状态的线程安全访问。

### 生命周期管理

同时处理多个服务器的连接建立、工具发现、注册和清理。

## 错误处理

- **服务器初始化失败**: 记录错误，继续其他服务器（除非 `fail_then_raise=True`）
- **工具执行错误**: 由各个 `MCPClient` 处理，返回结构化错误 JSON
- **重复工具**: 自动重映射并记录警告日志
- **连接丢失**: 下次工具调用时自动重试

## 相关文档

- [MCPClient](MCPClient.md) - 单个客户端管理
- [ToolsManager](ToolsManager.md) - 工具注册系统
- [MCP 服务集成](../../guide/extensions-integration/mcp-server-integration.md) - 综合集成指南
- [AmritaConfig](AmritaConfig.md) - 基于配置的设置
