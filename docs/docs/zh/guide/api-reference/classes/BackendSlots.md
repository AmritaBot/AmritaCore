# BackendSlots

`BackendSlots` 数据类持有 `ChatObject` 在运行时用于数据 I/O 的两个后端引用。

## 描述

`BackendSlots` 是一个简单的数据类，把 [AbilityBackend](AbilityBackend.md) 与 [MemoryBackend](MemoryBackend.md) 打包在一起，以便作为单个参数传给 `ChatObject` 或 `AgentRuntime`。

## 字段

- `ability` ([AbilityBackend](AbilityBackend.md))：负责加载工具、MCP 客户端和预设的后端
- `memory` ([MemoryBackend](MemoryBackend.md))：负责加载和提交对话记忆的后端
- `billing` ([BillingBackend](BillingBackend.md))：逐请求计费记录的可选接收端。默认值为一个 `LegacyBackend`，因此该槽位永不为 `None`

## 使用

```python
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

bkd = LegacyBackend()
slot = BackendSlots(ability=bkd, memory=bkd)

chat = ChatObject(
    train=train,
    user_input="你好",
    session_id="my_session",
    backend=slot,
)
```

## 默认行为

当 `backend=None` 传递给 `ChatObject` 或 `AgentRuntime` 时，`BackendSlots.default()` 用**同一个共享** `LegacyBackend` 实例构建全部三个槽位：

```python
bkd = LegacyBackend()
slot = BackendSlots(ability=bkd, memory=bkd, billing=bkd)
```

即能力、记忆与计费存储都使用进程内容器。

> `billing` 是唯一带默认值的字段，且它有自己的独立兜底：手工构造 `BackendSlots` 时若省略它，会为计费单独新建一个 `LegacyBackend`，与你传入的 `ability` / `memory` 后端**不共享状态**。
