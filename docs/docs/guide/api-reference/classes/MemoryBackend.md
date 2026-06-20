# MemoryBackend

Abstract base class for backends that provide memory (conversation history) persistence.

## Description

`MemoryBackend` defines the interface for loading and committing conversation memory. Subclasses must implement both methods.

## Methods

### `load_memory(session_id: str) -> MemoryModel`

Load conversation memory for a given session.

**Parameters**:

- `session_id` (str): The session identifier

**Returns**: [MemoryModel](MemoryModel.md) - The conversation memory

### `commit_memory(session_id: str, memory: MemoryModel) -> None`

Persist conversation memory for a given session.

**Parameters**:

- `session_id` (str): The session identifier
- `memory` ([MemoryModel](MemoryModel.md)): The memory model to persist

## Built-in Implementation

- [`LegacyBackend`](LegacyBackend.md): Default in-process implementation that stores memory in a `StateContext` container
