# MemoryModel

The MemoryModel class stores conversation history and context.

## Properties

- `messages` (list): List of messages in the conversation
- `time` (float): Timestamp
- `abstract` (str): Summary

## Example

```python
from amrita_core.types import MemoryModel, Message

memory = MemoryModel()
memory.messages.append(Message(content="Hello", role="user"))
memory.messages.append(Message(content="Hi there", role="assistant"))
```

## Description

The MemoryModel class inherits from BaseModel and is used to store conversation history, timestamps, and summary information. It is an important component for managing conversation context.
