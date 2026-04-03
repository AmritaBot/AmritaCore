# MultiClientManager

MultiClientManager 类为管理多个 MCP（Model Context Protocol）服务器连接和工具注册提供基础功能。

## 概述

MultiClientManager 处理连接到多个 MCP 服务器的复杂性，发现它们的工具，通过自动重映射解决命名冲突，并将所有工具注册到集中的 ToolsManager 中。它作为 ClientManager 单例实现的基础。

## 属性

- `clients` (list[MCPClient]): 所有已注册 MCP 客户端的列表
- `script_to_clients` (dict[str, MCPClient]): 从服务器脚本路径到客户端实例的映射
- `name_to_clients` (dict[str, MCPClient]): 从工具名称到其所属客户端的映射
- `tools_remapping` (dict[str, str]): 工具名称重映射字典（原始名称 → 重映射后的名称）
- `reversed_remappings` (dict[str, str]): 反向重映射字典（重映射后的名称 → 原始名称）
- `tools_manager` (MultiToolsManager): MCP 工具注册的工具管理器
- `_is_initialized` (bool): 是否所有客户端都已初始化
- `_lock` (asyncio.Lock): 用于线程安全操作的异步锁

## 方法

### `__init__() -> None`

初始化新的 MultiClientManager 实例。

**示例：**

```python
from amrita_core.tools.mcp import MultiClientManager

manager = MultiClientManager()
```

### `get_client_by_script(server_script: str | Path) -> MCPClient`

为特定服务器脚本创建新的 MCP 客户端，但不注册它。

**参数：**

- `server_script`: MCP 服务器脚本的路径或 URI

**返回值：**

- `MCPClient`: 新的、未连接的客户端实例

**示例：**

```python
client = manager.get_client_by_script("/path/to/server.mcp")
```

### `async get_client_by_tool_name(tool_name: str) -> MCPClient`

按工具名称查找拥有特定工具的 MCP 客户端。

**参数：**

- `tool_name`: 工具名称（自动处理重映射的名称）

**返回值：**

- `MCPClient`: 管理此工具的客户端实例

**异常：**

- `RuntimeError`: 如果在任何已注册的客户端中都找不到该工具

**示例：**

```python
client = await manager.get_client_by_tool_name("get_weather")
print(f"工具所有者：{client.server_script}")
```

### `register_only(*, client: MCPClient) -> Self`

注册一个 MCP 客户端但不初始化它。

**参数：**

- `client`: 预创建的 MCP 客户端实例

**返回值：**

- `Self`: 用于方法链式调用

**示例：**

```python
custom_client = MCPClient("/special/server.mcp")
manager.register_only(client=custom_client)
```

### `register_only(*, server_script: str | Path) -> Self`

按脚本路径注册 MCP 服务器但不初始化它。

**参数：**

- `server_script`: MCP 服务器脚本的路径

**返回值：**

- `Self`: 用于方法链式调用

**示例：**

```python
manager.register_only(server_script="/path/to/server.mcp")
```

### `async initialize_this(server_script: str | Path, fail_then_raise: bool = False) -> Self`

注册并初始化单个 MCP 服务器。

**参数：**

- `server_script`: MCP 服务器脚本的路径
- `fail_then_raise`: 如果为 True，初始化失败时抛出异常

**返回值：**

- `Self`: 用于方法链式调用

**示例：**

```python
await manager.initialize_this("/path/to/weather.mcp")
```

### `async initialize_scripts_all(scripts: Iterable[str | Path]) -> Self`

从脚本路径的可迭代对象初始化多个 MCP 服务器。

**参数：**

- `scripts`: 服务器脚本路径的可迭代对象

**返回值：**

- `Self`: 用于方法链式调用

**示例：**

```python
scripts = ["/path/to/weather.mcp", "/path/to/database.mcp"]
await manager.initialize_scripts_all(scripts)
```

### `async initialize_all(lock: bool = True) -> Self`

连接到所有已注册的 MCP 服务器并注册它们的工具。

**参数：**

- `lock`: 如果为 True，初始化前获取内部锁

**返回值：**

- `Self`: 完成后将 `_is_initialized` 设置为 True

**示例：**

```python
# 先注册服务器
manager.register_only(server_script="/server1.mcp")
manager.register_only(server_script="/server2.mcp")

# 然后一次性初始化所有
await manager.initialize_all()
```

### `async update_tools(client: MCPClient) -> Self`

更新特定客户端的工具，使用冲突解决机制重新注册它们。

**参数：**

- `client`: 需要更新工具的客户端

**返回值：**

- `Self`: 用于方法链式调用

**示例：**

```python
await manager.update_tools(existing_client)
```

### `async unregister_client(script_name: str | Path, lock: bool = True) -> None`

注销 MCP 服务器并从工具管理器中移除其所有工具。

**参数：**

- `script_name`: 要移除的服务器脚本路径
- `lock`: 如果为 True，操作期间获取内部锁

**示例：**

```python
await manager.unregister_client("/path/to/remove.mcp")
```

### `async reinitalize_all() -> None`

重新初始化所有已注册的客户端（用于在故障后刷新连接）。

**示例：**

```python
await manager.reinitalize_all()
```

### `_tools_wrapper(tool_name: str) -> Callable[[dict[str, Any]], Awaitable[str]]`

创建工具执行的包装函数，可注册为工具处理程序。

**参数：**

- `tool_name`: 要包装的工具名称

**返回值：**

- `Callable`: 接受工具参数并返回结果的异步函数

**注意：** 这是用于工具注册的内部方法。

### `_load_this(client: MCPClient, fail_then_raise: bool = True) -> None`

从客户端加载工具并使用冲突解决机制注册它们的内部方法。

**参数：**

- `client`: 需要加载工具的客户端
- `fail_then_raise`: 如果为 True，工具加载失败时抛出异常

**注意：** 这是在初始化期间调用的内部方法。

## 关键特性

### 自动工具注册

来自已注册 MCP 服务器的所有工具会自动发现并添加到 `tools_manager`，使它们立即可供 Agent 使用。

### 工具名称冲突解决

当多个服务器提供相同名称的工具时：

- 第一次注册保留原始名称
- 后续注册会自动重映射（例如 `search` → `referred_42_search`）
- 检测到每个冲突时都会生成警告日志
- 重映射信息存储在 `tools_remapping` 和 `reversed_remappings` 字典中

### 智能路由

`get_client_by_tool_name()` 方法自动解析哪个客户端拥有某个工具，透明地处理原始名称和重映射后的名称。

### 线程安全

所有关键操作都受异步锁（`_lock`）保护，确保在管理并发操作时对共享状态的线程安全访问。

### 生命周期管理

处理多个 MCP 连接的完整生命周期：

- 连接建立
- 工具发现和格式转换
- 工具注册及冲突处理
- 连接清理和重新初始化

## 完整使用示例

```python
import asyncio
from amrita_core.tools.mcp import MultiClientManager

async def main():
    # 创建管理器实例
    manager = MultiClientManager()

    # 方法 1：编程式设置
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

    # 查找哪个客户端拥有特定工具
    weather_client = await manager.get_client_by_tool_name("get_weather")
    print(f"天气工具提供者：{weather_client.server_script}")

    # 处理重复工具名称（自动重映射）
    # 如果两个服务器都有 "search" 工具：
    # - 第一个服务器保留 "search"
    # - 第二个服务器变成 "referred_42_search"

    # 在运行时动态添加新服务器
    await manager.initialize_this("/dynamic/new-server.mcp")

    # 移除服务器及其工具
    await manager.unregister_client("/path/to/old-server.mcp")

    # 刷新所有连接（例如在网络问题后）
    await manager.reinitalize_all()

    # 手动客户端管理
    custom_client = manager.get_client_by_script("/special/server.mcp")
    manager.register_only(client=custom_client)
    await manager.initialize_all()

asyncio.run(main())
```

## 错误处理

MultiClientManager 包含强大的错误处理机制：

- **服务器初始化失败**: 记录错误并继续其他服务器（除非 `fail_then_raise=True`）
- **工具执行错误**: 由各个 MCPClient 实例处理，返回结构化错误 JSON
- **重复工具名称**: 自动重映射并记录警告日志
- **连接丢失**: 通过 `reinitalize_all()` 在下次工具调用时自动重试
- **线程安全违规**: 通过异步锁机制防止

## 与 ClientManager 的关系

[`ClientManager`](ClientManager.md) 扩展了 MultiClientManager 并添加了：

- **单例模式**: 确保每个应用程序只有一个实例存在
- **全局访问**: 可以通过 `ClientManager()` 从任何地方访问
- **配置集成**: 与 AmritaConfig 的 MCP 设置无缝协作

对于大多数使用场景，建议优先使用 ClientManager 而不是直接实例化 MultiClientManager。

## 相关文档

- [ClientManager](ClientManager.md) - 用于全局访问的单例包装器
- [MCPClient](MCPClient.md) - 单个客户端管理
- [ToolsManager](ToolsManager.md) - 工具注册系统
- [MCP 服务集成](../../guide/extensions-integration/mcp-server-integration.md) - 综合集成指南
