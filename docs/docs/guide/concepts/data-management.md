# Data Management

AmritaCore's data management is split into three focused topics:

- [**Data Containers**](data-containers.md) — `Message`, `MemoryModel`, `TextContent`, `ImageContent`, `FileContent`, `ToolResult`, `StateContext`, `AbilityContext`, `CONTENT_LIST_TYPE`
- [**Data Backend**](data-backend.md) — `BackendSlots`, `AbilityBackend`, `MemoryBackend`, `LegacyBackend`, custom backends, `DatabackendOptions`
- [**Data Misc**](data-misc.md) — `ModelConfig`, `ModelPreset`, `ThinkingConfig`, `PresetManager`, `UniResponse`, `SendMessageWrap`, `EmbeddingChunk`, `register_content`, dirty tracking

> **Note**: The old `SessionsManager` / `SessionData` API has been replaced by the backend mechanism. Session isolation is now handled by `BackendSlots` with `LegacyBackend` (global container) or custom backends.
