# MemoryBackend

为提供记忆（对话历史）持久化的后端定义的抽象基类。

## 方法

### `load_memory(session_id: str) -> MemoryModel`

加载给定会话的对话记忆。

**返回**：[MemoryModel](MemoryModel.md) - 对话记忆

### `commit_memory(session_id: str, memory: MemoryModel) -> None`

持久化给定会话的对话记忆。

**参数**：

- `session_id` (str)：会话标识符
- `memory` ([MemoryModel](MemoryModel.md))：要持久化的记忆模型

## 内置实现

- [`LegacyBackend`](LegacyBackend.md)：默认的进程内实现，将记忆存储在 `StateContext` 容器中
