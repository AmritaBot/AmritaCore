# MemoryModel

MemoryModel 类存储对话历史和上下文。

## 继承

`MemoryModel` 继承自 `DirtyAwareBaseModel`（结合了 `BaseModel` 与脏标记跟踪），对所有字段启用自动变更跟踪。

## 属性

- `messages` (list)：对话中的消息列表
- `time` (float)：时间戳
- `abstract` (str)：历史压缩产生的摘要。当 `LLMConfig.enable_compaction` 开启时，由 train 模板渲染进系统指令
- `usage` (`UniResponseUsage` | None)：provider 为最近一次请求上报的用量。驱动压缩触发；每次折叠后被清空
- `billing` (list[[BillingRecord](BillingRecord.md)])：本会话累积的逐请求计费记录。这是成本数据的默认持久化路径
- `dirty_exclude__` (`tuple[str, ...]`)：脏跟踪需要忽略的字段名；默认为 `("model_config",)`

> 该模型允许额外键（`extra="allow"`），消费方无需继承即可附加自己的字段。

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
