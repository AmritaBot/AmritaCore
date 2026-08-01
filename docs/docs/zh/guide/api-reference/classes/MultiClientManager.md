# MultiClientManager

MultiClientManager 类提供管理多个 MCP 服务器连接和工具注册的基础功能。

## 概述

MultiClientManager 处理连接多个 MCP 服务器、发现其工具、通过自动重映射解决命名冲突以及将所有工具注册到集中式 ToolsManager 的复杂性。它作为 ClientManager 单例实现的基础。

## 属性

- `clients` (list[MCPClient])：所有已注册 MCP 客户端的列表
- `script_to_clients` (dict[str, MCPClient])：服务器脚本路径到客户端实例的映射
- `name_to_clients` (dict[str, MCPClient])：工具名到其所属客户端的映射
- `tools_remapping` (dict[str, str])：工具名重映射字典（原始名 → 重映射名）
- `reversed_remappings` (dict[str, str])：反向重映射字典（重映射名 → 原始名）
- `tools_manager` (MultiToolsManager)：MCP 工具注册到的工具管理器

## 方法

### `get_client_by_script(server_script: str | Path) -> MCPClient`

为特定服务器脚本创建新的 MCP 客户端，不注册。

### `async get_client_by_tool_name(tool_name: str) -> MCPClient`

按工具名查找拥有该工具的 MCP 客户端。

### `async initialize_scripts_all(scripts: list[str | Path]) -> None`

初始化并注册所有提供的 MCP 服务器脚本。
