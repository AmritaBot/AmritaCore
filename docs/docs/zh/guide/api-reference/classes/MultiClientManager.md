# MultiClientManager

MultiClientManager 类提供管理多个 MCP（Model Context Protocol）服务器连接和工具注册的基础功能。

## 概述

MultiClientManager 处理连接多个 MCP 服务器、发现其工具、通过自动重映射解决命名冲突以及将所有工具注册到集中式 ToolsManager 的复杂性。它作为 ClientManager 单例实现的基础。

## 属性

- `clients` (list[MCPClient])：所有已注册 MCP 客户端的列表
- `script_to_clients` (dict[str, MCPClient])：服务器脚本路径到客户端实例的映射
- `name_to_clients` (dict[str, MCPClient])：工具名到其所属客户端的映射
- `tools_remapping` (dict[str, str])：工具名重映射字典（原始名 → 重映射名）
- `reversed_remappings` (dict[str, str])：反向重映射字典（重映射名 → 原始名）
- `tools_manager` (MultiToolsManager)：MCP 工具注册到的工具管理器
- `_is_initialized` (bool)：所有客户端是否已初始化
- `_lock` (asyncio.Lock)：用于线程安全操作的异步锁

## 方法

### `__init__() -> None`

初始化一个新的 MultiClientManager 实例。

**示例：**

```python
from amrita_core.tools.mcp import MultiClientManager

manager = MultiClientManager()
```

### `get_client_by_script(server_script: str | Path) -> MCPClient`

为特定服务器脚本创建新的 MCP 客户端，但不注册它。

**参数：**

- `server_script`：MCP 服务器脚本路径或 URI

**返回：**

- `MCPClient`：一个新的、尚未连接的客户端实例

**示例：**

```python
client = manager.get_client_by_script("/path/to/server.mcp")
```

### `async get_client_by_tool_name(tool_name: str) -> MCPClient`

按名称查找拥有某个工具的 MCP 客户端。

**参数：**

- `tool_name`：工具名（会自动处理重映射后的名称）

**返回：**

- `MCPClient`：管理该工具的客户端实例

**抛出：**

- `RuntimeError`：若在任何已注册的客户端中都找不到该工具

**示例：**

```python
client = await manager.get_client_by_tool_name("get_weather")
print(f"Tool owner: {client.server_script}")
```

### `register_only(*, client: MCPClient) -> Self`

注册一个 MCP 客户端但不初始化它。

**参数：**

- `client`：预先创建的 MCP 客户端实例

**返回：**

- `Self`：便于链式调用

**示例：**

```python
custom_client = MCPClient("/special/server.mcp")
manager.register_only(client=custom_client)
```

### `register_only(*, server_script: str | Path) -> Self`

按脚本路径注册一个 MCP 服务器但不初始化它。

**参数：**

- `server_script`：MCP 服务器脚本路径

**返回：**

- `Self`：便于链式调用

**示例：**

```python
manager.register_only(server_script="/path/to/server.mcp")
```

### `async initialize_this(server_script: str | Path, fail_then_raise: bool = False) -> Self`

注册并初始化单个 MCP 服务器。

**参数：**

- `server_script`：MCP 服务器脚本路径
- `fail_then_raise`：为 True 时，初始化失败会抛出异常

**返回：**

- `Self`：便于链式调用

**示例：**

```python
await manager.initialize_this("/path/to/weather.mcp")
```

### `async initialize_scripts_all(scripts: Iterable[str | Path]) -> Self`

从脚本路径的可迭代对象初始化多个 MCP 服务器。

**参数：**

- `scripts`：服务器脚本路径的可迭代对象

**返回：**

- `Self`：便于链式调用

**示例：**

```python
scripts = ["/path/to/weather.mcp", "/path/to/database.mcp"]
await manager.initialize_scripts_all(scripts)
```

### `async initialize_all(lock: bool = True) -> Self`

连接所有已注册的 MCP 服务器并注册其工具。

**参数：**

- `lock`：为 True 时，在初始化前获取内部锁

**返回：**

- `Self`：完成后将 `_is_initialized` 设为 True

**示例：**

```python
# Register servers first
manager.register_only(server_script="/server1.mcp")
manager.register_only(server_script="/server2.mcp")

# Then initialize all at once
await manager.initialize_all()
```

### `async update_tools(client: MCPClient) -> Self`

更新特定客户端的工具，并以冲突解决方式重新注册它们。

**参数：**

- `client`：需要更新其工具的客户端

**返回：**

- `Self`：便于链式调用

**示例：**

```python
await manager.update_tools(existing_client)
```

### `async unregister_client(script_name: str | Path, lock: bool = True) -> None`

注销一个 MCP 服务器，并从工具管理器中移除其所有工具。

**参数：**

- `script_name`：要移除的服务器脚本路径
- `lock`：为 True 时，在操作期间获取内部锁

**示例：**

```python
await manager.unregister_client("/path/to/remove.mcp")
```

### `async reinitialize_all() -> None`

重新初始化所有已注册的客户端（适用于在失败后刷新连接）。

**示例：**

```python
await manager.reinitialize_all()
```

### `_tools_wrapper(tool_name: str) -> Callable[[dict[str, Any]], Awaitable[str]]`

创建一个工具执行的包装函数，可作为工具处理器注册。

**参数：**

- `tool_name`：要包装的工具名

**返回：**

- `Callable`：接受工具参数并返回结果的异步函数

**注意：** 用于工具注册的内部方法。

### `_load_this(client: MCPClient, fail_then_raise: bool = True) -> None`

从客户端加载工具并以冲突解决方式注册它们的内部方法。

**参数：**

- `client`：需要加载其工具的客户端
- `fail_then_raise`：为 True 时，工具加载失败会抛出异常

**注意：** 这是初始化期间调用的内部方法。

## 关键特性

### 自动工具注册

来自已注册 MCP 服务器的所有工具都会被自动发现并加入 `tools_manager`，从而立即可供 agent 使用。

### 工具名冲突解决

当多个服务器提供同名工具时：

- 首次注册保留原名
- 后续注册会被自动重映射（例如 `search` → `referred_42_search`）
- 每检测到一个冲突都会生成警告日志
- 重映射信息存储在 `tools_remapping` 和 `reversed_remappings` 字典中

### 智能路由

`get_client_by_tool_name()` 方法会自动解析哪个客户端拥有某个工具，透明地处理原始名称和重映射后的名称。

### 线程安全

所有关键操作都由一把异步锁（`_lock`）保护，确保在管理并发操作时对共享状态的线程安全访问。

### 生命周期管理

处理多个 MCP 连接的完整生命周期：

- 建立连接
- 工具发现与格式转换
- 带冲突处理的工具注册
- 连接清理与重新初始化

## 完整使用示例

```python
import asyncio
from amrita_core.tools.mcp import MultiClientManager


async def main():
    # Create manager instance
    manager = MultiClientManager()

    # Method 1: Programmatic setup
    scripts = ["/path/to/weather.mcp", "/path/to/database.mcp", "/path/to/calendar.mcp"]

    # Register and initialize all servers
    await manager.initialize_scripts_all(scripts)

    # Check available tools
    available_tools = manager.tools_manager.get_tools()
    print(f"Available tools: {list(available_tools.keys())}")

    # Find which client owns a specific tool
    weather_client = await manager.get_client_by_tool_name("get_weather")
    print(f"Weather tool provided by: {weather_client.server_script}")

    # Handle duplicate tool names (automatic remapping)
    # If two servers both have a "search" tool:
    # - First server keeps "search"
    # - Second server becomes "referred_42_search"

    # Dynamically add a new server at runtime
    await manager.initialize_this("/dynamic/new-server.mcp")

    # Remove a server and its tools
    await manager.unregister_client("/path/to/old-server.mcp")

    # Refresh all connections (e.g., after network issues)
    await manager.reinitialize_all()

    # Manual client management
    custom_client = manager.get_client_by_script("/special/server.mcp")
    manager.register_only(client=custom_client)
    await manager.initialize_all()


asyncio.run(main())
```

## 错误处理

MultiClientManager 包含健壮的错误处理：

- **服务器初始化失败**：记录错误并继续处理其他服务器（除非 `fail_then_raise=True`）
- **工具执行错误**：由各自的 MCPClient 实例处理，返回结构化的错误 JSON
- **重复工具名**：自动重映射并输出警告日志
- **连接丢失**：在下次工具调用时通过 `reinitialize_all()` 自动重试
- **线程安全违规**：由异步锁机制防止

## 与 ClientManager 的关系

[`ClientManager`](ClientManager.md) 继承 MultiClientManager 并新增：

- **单例模式**：确保每个应用只存在一个实例
- **全局可访问**：可通过 `ClientManager()` 从任何地方访问
- **配置集成**：与 AmritaConfig 的 MCP 设置无缝协作

在大多数场景下，优先使用 ClientManager，而不是直接实例化 MultiClientManager。

## 相关文档

- [ClientManager](ClientManager.md) - 用于全局访问的单例封装
- [MCPClient](MCPClient.md) - 单个客户端管理
- `ToolsManager` - 工具注册系统
- [MCP 服务器集成](../../extensions-integration/mcp-server.md) - 完整的集成指南
