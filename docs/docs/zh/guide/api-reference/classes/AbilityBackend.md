# AbilityBackend

提供能力相关数据（工具、MCP 客户端、预设）的后端的抽象基类。

## 描述

`AbilityBackend` 定义了从持久化层加载能力上下文的接口。子类必须实现全部四个方法。

## 方法

### `load_ability_all(session_id: str) -> AbilityContext`

加载给定会话的完整能力上下文。

**参数**：

- `session_id` (str): 会话标识符

**返回**: [AbilityContext](AbilityContext.md) - 完整的能力上下文

### `load_mcp_clients(session_id: str) -> MultiClientManager`

加载给定会话的 MCP 客户端。

**参数**：

- `session_id` (str): 会话标识符

**返回**: `MultiClientManager` - MCP 客户端管理器

### `load_tools(session_id: str) -> MultiToolsManager`

加载给定会话的工具。

**参数**：

- `session_id` (str): 会话标识符

**返回**: `MultiToolsManager` - 工具管理器

### `load_presets(session_id: str) -> MultiPresetManager`

加载给定会话的预设。

**参数**：

- `session_id` (str): 会话标识符

**返回**: `MultiPresetManager` - 预设管理器

## 内置实现

- [`LegacyBackend`](LegacyBackend.md): 默认的进程内实现，将数据存储在全局容器中
