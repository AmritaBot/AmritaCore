# MemoryModel

MemoryModel 类存储对话历史和上下文。

## 继承

`MemoryModel` 继承自 `DirtyAwareBaseModel`（结合了 `BaseModel` 与脏标记跟踪），对所有字段启用自动变更跟踪。

## 属性

- `messages` (list)：对话中的消息列表
- `time` (float)：时间戳
- `abstract` (str)：摘要

## 脏跟踪方法

继承自 `DirtyAwareBaseModel`：

- `is_dirty(name: str | None = None) -> bool`：检查特定属性是否被修改
- `get_dirty_vars() -> set[str]`：返回所有脏属性名称的集合
- `clean()`：重置脏状态，清除所有跟踪的变更

## 示例

```python
from amrita_core.types import MemoryModel, Message

memory = MemoryModel()
memory.messages.append(Message(content="你好", role="user"))
memory.messages.append(Message(content="你好呀", role="assistant"))

assert memory.is_dirty("messages")  # True
memory.clean()
assert not memory.is_dirty()  # True
```
