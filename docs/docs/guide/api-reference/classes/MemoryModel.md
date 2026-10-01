# MemoryModel

The MemoryModel class stores conversation history and context.

## Inheritance

`MemoryModel` extends `DirtyAwareBaseModel` (which itself combines `BaseModel` with dirty-mark tracking), enabling automatic mutation tracking on all fields.

## Properties

- `messages` (list): List of messages in the conversation
- `time` (float): Timestamp
- `abstract` (str): Summary produced by history compaction. Rendered into the system instruction by the train template when `LLMConfig.enable_compaction` is on
- `usage` (`UniResponseUsage` | None): The usage the provider reported for the most recent request. Drives the compaction trigger, and is cleared after each fold
- `billing` (list[[BillingRecord](BillingRecord.md)]): Per-request billing records accumulated for this session. This is the default persistence path for cost data
- `dirty_exclude__` (`tuple[str, ...]`): Names of fields the dirty tracker must ignore; defaults to `("model_config",)`

> The model allows extra keys (`extra="allow"`), so consumers can attach their own fields without subclassing.

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
