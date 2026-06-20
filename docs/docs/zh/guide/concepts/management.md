# 数据管理

AmritaCore 的数据管理分为三个专题：

- [**数据容器**](data-containers.md) — `Message`、`MemoryModel`、`TextContent`、`ImageContent`、`FileContent`、`ToolResult`、`StateContext`、`AbilityContext`、`CONTENT_LIST_TYPE`
- [**数据后端**](data-backend.md) — `BackendSlots`、`AbilityBackend`、`MemoryBackend`、`LegacyBackend`、自定义后端、`DatabackendOptions`
- [**数据杂项**](data-misc.md) — `ModelConfig`、`ModelPreset`、`ThinkingConfig`、`PresetManager`、`UniResponse`、`SendMessageWrap`、`EmbeddingChunk`、`register_content`、脏标记追踪

> **注意**：旧的 `SessionsManager` / `SessionData` API 已被后端机制取代。会话隔离现在由 `BackendSlots` 配合 `LegacyBackend`（全局容器）或自定义后端处理。
