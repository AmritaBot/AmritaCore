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

清理指定键下的运行中聊天对象，最多保留 `maxitems` 个对象。

**参数：**

- `k` (`str`)：会话 ID 键
- `maxitems` (`int`, 可选)：最多保留的对象数。默认 `10`

**返回：** `bool` — 执行了清理则返回 `True`

### `get_all_objs() -> list[ChatObjectMeta]`

获取所有会话中所有运行中聊天对象的元数据。

**返回：** `list[ChatObjectMeta]`

### `get_objs(session_id: str) -> list[ChatObject]`

获取给定会话 ID 的所有活跃聊天对象。

**参数：**

- `session_id` (`str`)：用户会话 ID

**返回：** `list[ChatObject]`
