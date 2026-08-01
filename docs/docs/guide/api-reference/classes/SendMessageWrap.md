# SendMessageWrap

The SendMessageWrap class is an iterable wrapper for message lists sent to the model.

## Description

SendMessageWrap (implementing `Iterable[Message | ToolResult]`) organizes the full message context into four parts: system `train` message, `memory` messages (without system message), the `user_query`, and `end_messages`. Iterating yields `train`, then `memory`, then `user_query`.

## Properties

- `train` (Message[str]): System message
- `memory` (list[Message | ToolResult]): Messages without the system message
- `user_query` (Message): The user's query message
- `end_messages` (list[Message | ToolResult]): End messages (appended at the end)

## Constructor

- `__init__(train: dict | Message, memory: list | MemoryModel, user_query: Message | None = None)`: Builds the wrapper. If `user_query` is omitted, the last memory message is used; it must be a user message (raises `ValueError` otherwise), and is popped from `memory` when auto-detected

## Methods

- `classmethod validate_messages(messages: list) -> SendMessageWrap`: Builds a wrapper from a message list, locating the system message as `train` (raises `ValueError` if none found)
- `__len__() -> int`: `len(memory) + 2 + len(end_messages)`
- `__iter__()`: Yields `train`, then `memory`, then `user_query`

## Example

```python
from amrita_core.types import SendMessageWrap

wrap = SendMessageWrap(
    train={"role": "system", "content": "You are a helpful assistant."},
    memory=[{"role": "user", "content": "Hello!"}],
)
for msg in wrap:
    print(msg.role, msg.get_content())
```
