# BackendSlots

`BackendSlots` 数据类持有 `ChatObject` 运行时用于数据 I/O 的两个后端引用。

## 描述

`BackendSlots` 是一个简单的数据类，它将 [AbilityBackend](AbilityBackend.md) 和 [MemoryBackend](MemoryBackend.md) 捆绑在一起，以便作为单个参数传递给 `ChatObject` 或 `AgentRuntime`。

## 字段

- `ability` ([AbilityBackend](AbilityBackend.md)): 负责加载工具、MCP 客户端和预设的后端
- `memory` ([MemoryBackend](MemoryBackend.md)): 负责加载和提交对话记忆的后端

## 用法

```python
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

bkd = LegacyBackend()
slot = BackendSlots(ability=bkd, memory=bkd)

# 传递给 ChatObject
chat = ChatObject(
    train=train,
    user_input="Hello",
    session_id="my_session",
    backend=slot,
)
```

## 默认行为

当 `backend=None` 传递给 `ChatObject` 或 `AgentRuntime` 时，默认值为：

```python
bkd = LegacyBackend()
slot = BackendSlots(bkd, bkd)
```

这将对记忆和能力存储都使用进程内全局容器。
