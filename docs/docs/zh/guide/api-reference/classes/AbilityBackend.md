# AbilityBackend

为提供能力相关数据（工具、MCP 客户端、预设）的后端定义的抽象基类。

## 方法

### `load_ability_all(session_id: str) -> AbilityContext`

加载给定会话的完整能力上下文。

### `load_mcp_clients(session_id: str) -> MultiClientManager`

加载给定会话的 MCP 客户端。

### `load_tools(session_id: str) -> MultiToolsManager`

加载给定会话的工具。

### `load_presets(session_id: str) -> MultiPresetManager`

加载给定会话的预设。

## 内置实现

- [`LegacyBackend`](LegacyBackend.md)：默认的进程内实现，将数据存储在全局容器中
