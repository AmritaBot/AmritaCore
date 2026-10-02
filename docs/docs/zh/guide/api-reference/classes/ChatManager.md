# ChatManager

`ChatManager` 管理运行中的 `ChatObject` 实例，提供清理、查找和注册功能。

## 概述

`ChatManager` 是一个数据类，维护两个数据结构：

- `running_chat_object`：将会话 ID 映射到活跃 `ChatObject` 实例列表的字典
- `running_chat_object_id2map`：将流 ID 映射到 `ChatObjectMeta` 元数据快照的字典

全局单例 `chat_manager` 可供方便使用。

## 属性

| 属性                         | 类型                                 | 描述                         |
| ---------------------------- | ------------------------------------ | ---------------------------- |
| `running_chat_object`        | `defaultdict[str, list[ChatObject]]` | 按会话 ID 分组的活跃聊天对象 |
| `running_chat_object_id2map` | `dict[str, ChatObjectMeta]`          | 按流 ID 索引的元数据快照     |
| `_lock`                      | `aiologic.Lock`                      | 线程安全的异步锁             |

## 方法

### `clean_obj(k: str, maxitems: int = 10) -> bool`

清理指定键下的运行中聊天对象，最多保留 `maxitems` 个对象。超出上限的已完成对象会
被移除，未完成的对象则保留。

**参数：**

- `k` (`str`)：会话 ID 键
- `maxitems` (`int`, 可选)：最多保留的对象数。默认 `10`

**返回：** `bool` — 执行了清理则返回 `True`，否则返回 `False`

### `get_all_objs() -> list[ChatObjectMeta]`

获取所有会话中所有运行中聊天对象的元数据。

**返回：** `list[ChatObjectMeta]` — 全部运行中聊天对象元数据快照的列表

### `get_objs(session_id: str) -> list[ChatObject]`

获取给定会话 ID 的所有活跃聊天对象。

**参数：**

- `session_id` (`str`)：用户会话 ID

**返回：** `list[ChatObject]` — 该会话的聊天对象列表

### `async clean_chat_objects(maxitems: int = 10) -> None`

异步清理所有会话中的全部运行中聊天对象，每个会话限制为 `maxitems` 个。

**参数：**

- `maxitems` (`int`, 可选)：每个会话最多保留的对象数。默认 `10`

### `async add_chat_object(chat_object: ChatObject) -> None`

向管理器注册新的 `ChatObject` 实例。创建元数据快照，并把对象插入该会话列表的开头
。

**参数：**

- `chat_object` (`ChatObject`)：要注册的聊天对象实例

## 全局实例

有一个预先初始化好的全局单例：

```python
from amrita_core.chatmanager import chat_manager

# 直接使用
all_objects = chat_manager.get_all_objs()
```
