# ChatObjectMeta

`ChatObjectMeta` is a Pydantic `BaseModel` that stores identification, event, and timing metadata for a `ChatObject` instance.

## Overview

This model captures a snapshot of a chat object's state, primarily used by `ChatManager` for tracking and managing running chat objects.

## Fields

| Field        | Type                                       | Default                   | Description                        |
| ------------ | ------------------------------------------ | ------------------------- | ---------------------------------- |
| `stream_id`  | `str`                                      | —                         | Chat stream ID (unique identifier) |
| `session_id` | `str`                                      | —                         | Session ID this chat belongs to    |
| `user_input` | `list[TextContent \| ImageContent] \| str` | —                         | The user's input content           |
| `time`       | `datetime`                                 | `factory: datetime.now()` | Creation timestamp                 |
| `last_call`  | `datetime`                                 | `factory: datetime.now()` | Last interaction timestamp         |

## Usage

```python
from amrita_core.chatmanager import ChatObjectMeta

# The ChatObjectMeta is typically created internally
# by ChatManager.add_chat_object() from the chat object's snapshot

# Access metadata from ChatManager
from amrita_core.chatmanager import chat_manager

metas = chat_manager.get_all_objs()
for meta in metas:
    print(f"Session: {meta.session_id}, Stream: {meta.stream_id}")
    print(f"Created: {meta.time}, Last call: {meta.last_call}")
```
