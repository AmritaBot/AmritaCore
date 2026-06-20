# MemoryModel

MemoryModel 类存储对话历史和上下文。

## 继承关系

`MemoryModel` 继承自 [`DirtyAwareBaseModel`](DirtyAwareBaseModel.md)（它本身组合了 `BaseModel` 与脏标记追踪），从而实现对所有字段的自动变更追踪。

## 属性

- `messages` (list): 对话中的消息列表
- `time` (float): 时间戳
- `abstract` (str): 摘要

## 脏追踪方法

继承自 `DirtyAwareBaseModel`，这些方法允许检查字段是否被修改过：

- `is_dirty(name: str | None = None) -> bool`: 检查特定属性（或任意属性）是否已被修改
- `get_dirty_vars() -> set[str]`: 返回所有脏属性名称的集合
- `clean()`: 重置脏状态，清除所有追踪的变更

## 示例

```python
from amrita_core.types import MemoryModel, Message

memory = MemoryModel()
memory.messages.append(Message(content="Hello", role="user"))
memory.messages.append(Message(content="Hi there", role="assistant"))

# 检查脏状态
assert memory.is_dirty("messages")  # True — messages 已被修改
print("脏变量:", memory.get_dirty_vars())  # {'messages'}

memory.clean()  # 重置追踪
assert not memory.is_dirty()  # True — 没有待处理的变更
```

## 描述

MemoryModel 类继承自 DirtyAwareBaseModel，用于存储对话历史、时间戳和摘要信息。它是管理对话上下文的重要组件。脏标记机制允许后端高效地检测哪些字段发生了变化，并仅持久化已修改的部分。
