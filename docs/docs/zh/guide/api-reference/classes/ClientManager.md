# ClientManager

ClientManager 类为多个 MCP 服务器连接和工具注册提供集中管理。

## 概述

ClientManager 是一个**单例类，继承自 [`MultiClientManager`](MultiClientManager.md)**，继承其所有功能，同时添加了单例模式支持以实现全局可访问性。

## 继承

```text
ClientManager → MultiClientManager
```

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
