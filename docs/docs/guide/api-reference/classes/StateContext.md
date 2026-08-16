# StateContext

> **Deprecated**: scheduled for removal in **v0.14.0**. Using this class emits a `DeprecationWarning`. Use the DI contexts directly (`_di_session`, `_di_memory`, `_di_ability`) or the `session_id` / `data` / `config` properties on `ChatObject` instead.

A dataclass that holds the full runtime state for a `ChatObject` session.

## Description

`StateContext` is the runtime state container created and managed by `ChatObject` during execution. It holds the session ID, conversation memory, and ability context.

## Fields

- `session_id` (str): Unique identifier for the session. Auto-generated as a UUID hex string if not provided
- `memory` ([MemoryModel](MemoryModel.md)): The conversation memory model
- `ability` ([AbilityContext](AbilityContext.md)): The ability context (tools, presets, MCP clients)
- `extra` (dict[str, Any]): Additional custom data

## Usage

```python
from amrita_core.contexts import StateContext

# Auto-generated session ID
state = StateContext()
print(state.session_id)  # e.g., "a1b2c3d4e5f6..."

# With explicit session ID
state = StateContext(session_id="my_session")
print(state.session_id)  # "my_session"
```

> **Migration**: instead of creating a `StateContext` and passing it to
> `ChatObject(context=...)`, pass `session_id` directly and set `data`
> afterwards:
>
> ```python
> from amrita_core.chatmanager import ChatObject
>
> chat = ChatObject(user_input="...", session_id="my_session")
> chat.data = MemoryModel(messages=[...])  # instead of state.memory
> ```

## Notes

- `StateContext` is typically created internally by `ChatObject`. You only need to create one directly when you want to share state across multiple `ChatObject` instances (e.g., for multi-turn conversations without backend persistence)
