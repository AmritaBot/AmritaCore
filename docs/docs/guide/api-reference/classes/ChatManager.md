# ChatManager

`ChatManager` manages running `ChatObject` instances, providing cleanup, lookup, and registration functionality.

## Overview

`ChatManager` is a dataclass that maintains two data structures:

- `running_chat_object`: A dictionary mapping session IDs to lists of active `ChatObject` instances
- `running_chat_object_id2map`: A dictionary mapping stream IDs to `ChatObjectMeta` metadata snapshots

A global singleton instance `chat_manager` is available for convenience.

## Attributes

| Attribute                    | Type                                 | Description                               |
| ---------------------------- | ------------------------------------ | ----------------------------------------- |
| `running_chat_object`        | `defaultdict[str, list[ChatObject]]` | Active chat objects grouped by session ID |
| `running_chat_object_id2map` | `dict[str, ChatObjectMeta]`          | Metadata snapshots keyed by stream ID     |
| `_lock`                      | `aiologic.Lock`                      | Async lock for thread-safe operations     |

## Methods

### `clean_obj(k: str, maxitems: int = 10) -> bool`

Clean up running chat objects under the specified key, keeping only up to `maxitems` objects. Completed objects beyond the limit are removed; incomplete ones are preserved.

**Parameters:**

- `k` (`str`): Session ID key
- `maxitems` (`int`, optional): Maximum number of objects to keep. Defaults to `10`.

**Returns:** `bool` — `True` if cleanup was performed, `False` otherwise

---

### `get_all_objs() -> list[ChatObjectMeta]`

Get metadata for all running chat objects across all sessions.

**Returns:** `list[ChatObjectMeta]` — List of all running chat object metadata snapshots

---

### `get_objs(session_id: str) -> list[ChatObject]`

Get all active chat objects for a given session ID.

**Parameters:**

- `session_id` (`str`): User session ID

**Returns:** `list[ChatObject]` — List of chat objects for the session

---

### `async clean_chat_objects(maxitems: int = 10) -> None`

Asynchronously clean up all running chat objects across all sessions, limiting each session to `maxitems` objects.

**Parameters:**

- `maxitems` (`int`, optional): Maximum number of objects per session. Defaults to `10`.

---

### `async add_chat_object(chat_object: ChatObject) -> None`

Register a new `ChatObject` instance with the manager. Creates a metadata snapshot and inserts the object at the beginning of the session's list.

**Parameters:**

- `chat_object` (`ChatObject`): The chat object instance to register

## Global Instance

A pre-initialized global singleton is available:

```python
from amrita_core.chatmanager import chat_manager

# Use directly
all_objects = chat_manager.get_all_objs()
```
