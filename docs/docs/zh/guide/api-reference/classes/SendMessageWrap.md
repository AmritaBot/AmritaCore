# SendMessageWrap

SendMessageWrap 类是发送给模型的消息列表的可迭代包装器。

## 描述

SendMessageWrap（实现 `Iterable[Message | ToolResult]`）将完整消息上下文组织为四个部分：系统 `train` 消息、`memory` 消息（不含系统消息）、`user_query` 和 `end_messages`。迭代时按顺序生成 `train`、`memory`、`user_query`。

## 属性

- `train` (Message[str])：系统消息
- `memory` (list[Message | ToolResult])：不含系统消息的消息列表
- `user_query` (Message)：用户查询消息
- `end_messages` (list[Message | ToolResult])：末尾消息

## 构造函数

- `__init__(train: dict | Message, memory: list | MemoryModel, user_query: Message | None = None)`：构建包装器

## 方法

- `classmethod validate_messages(messages: list) -> SendMessageWrap`：从消息列表构建包装器
- `__len__() -> int`：`len(memory) + 2 + len(end_messages)`
- `__iter__()`：依次生成 `train`、`memory`、`user_query`

## 示例

```python
from amrita_core.types import SendMessageWrap

wrap = SendMessageWrap(
    train={"role": "system", "content": "You are a helpful assistant."},
    memory=[{"role": "user", "content": "Hello!"}],
)
for msg in wrap:
    print(msg.role, msg.get_content())
```
