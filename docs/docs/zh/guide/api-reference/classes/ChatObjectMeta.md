# ChatObjectMeta

`ChatObjectMeta` 是一个 Pydantic `BaseModel`，存储 `ChatObject` 实例的标识、事件和计时元数据。

## 概述

此模型捕获聊天对象状态的快照，主要由 `ChatManager` 用于跟踪和管理运行中的聊天对象。

## 字段

| 字段         | 类型                                       | 默认值                    | 描述                    |
| ------------ | ------------------------------------------ | ------------------------- | ----------------------- |
| `stream_id`  | `str`                                      | —                         | 聊天流 ID（唯一标识符） |
| `session_id` | `str`                                      | —                         | 所属会话 ID             |
| `user_input` | `list[TextContent \| ImageContent] \| str` | —                         | 用户输入内容            |
| `time`       | `datetime`                                 | `factory: datetime.now()` | 创建时间戳              |
| `last_call`  | `datetime`                                 | `factory: datetime.now()` | 最后交互时间戳          |

## 使用

```python
from amrita_core.chatmanager import ChatObjectMeta

# ChatObjectMeta 通常由 ChatManager.add_chat_object() 内部创建

# 从 ChatManager 访问元数据
from amrita_core.chatmanager import chat_manager

metas = chat_manager.get_all_objs()
for meta in metas:
    print(f"会话: {meta.session_id}, 流: {meta.stream_id}")
    print(f"创建: {meta.time}, 最后调用: {meta.last_call}")
```
