# Message

The Message class represents a single message in the conversation.

## Properties

- `role` (Literal["user", "assistant", "system"]): Role of the message
- `content` (T): Content of the message, where T is a generic parameter
- `tool_calls` (list[[ToolCall](ToolCall.md)] | None): List of tool calls, optional

## Example

```python
from amrita_core.types import Message

# Create different types of messages
system_msg = Message(content="You are a helpful assistant.", role="system")
user_msg = Message(content="Hello, how are you?", role="user")
assistant_msg = Message(content="I'm doing well, thank you!", role="assistant")
```

## Description

The Message class inherits from BaseModel and implements generics to represent messages in a conversation. It includes role, content, and optional tool call information.