# BackendSlots

`BackendSlots` 数据类持有 `ChatObject` 在运行时用于数据 I/O 的两个后端引用。

## 字段

- `ability` ([AbilityBackend](AbilityBackend.md))：负责加载工具、MCP 客户端和预设的后端
- `memory` ([MemoryBackend](MemoryBackend.md))：负责加载和提交对话记忆的后端

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

当 `backend=None` 传递给 `ChatObject` 或 `AgentRuntime` 时，默认为 `LegacyBackend()` 用于两个槽位。
