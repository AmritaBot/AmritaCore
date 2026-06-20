# MemoryModel

The MemoryModel class stores conversation history and context.

## Inheritance

`MemoryModel` extends [`DirtyAwareBaseModel`](DirtyAwareBaseModel.md) (which itself combines `BaseModel` with dirty-mark tracking), enabling automatic mutation tracking on all fields.

## Properties

- `messages` (list): List of messages in the conversation
- `time` (float): Timestamp
- `abstract` (str): Summary

## Dirty Tracking Methods

Inherited from `DirtyAwareBaseModel`, these methods allow checking whether fields have been modified:

- `is_dirty(name: str | None = None) -> bool`: Check whether a specific attribute (or any attribute) has been modified
- `get_dirty_vars() -> set[str]`: Return the set of all dirty attribute names
- `clean()`: Reset the dirty state, clearing all tracked changes

## Example

```python
from amrita_core.types import MemoryModel, Message

memory = MemoryModel()
memory.messages.append(Message(content="Hello", role="user"))
memory.messages.append(Message(content="Hi there", role="assistant"))

# Check dirty state
assert memory.is_dirty("messages")  # True — messages was modified
print("Dirty vars:", memory.get_dirty_vars())  # {'messages'}

memory.clean()  # Reset tracking
assert not memory.is_dirty()  # True — no pending changes
```

## Description

The MemoryModel class inherits from DirtyAwareBaseModel and is used to store conversation history, timestamps, and summary information. It is an important component for managing conversation context. The dirty-mark mechanism allows backends to efficiently detect which fields have changed and only persist the modified portions.
