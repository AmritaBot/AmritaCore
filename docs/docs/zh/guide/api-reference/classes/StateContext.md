# StateContext

> **已弃用**：计划在 **v0.14.0** 移除。使用本类会触发 `DeprecationWarning`。
> 请直接使用 DI 上下文（`_di_session`、`_di_memory`、`_di_ability`）或
> `ChatObject` 的 `session_id` / `data` / `config` 属性替代。

## 字段

- `session_id` (str)：会话的唯一标识符。如未提供则自动生成为 UUID 十六进制字符串
- `memory` ([MemoryModel](MemoryModel.md))：对话记忆模型
- `ability` ([AbilityContext](AbilityContext.md))：能力上下文（工具、预设、MCP 客户端）
- `extra` (dict[str, Any])：额外的自定义数据

## 使用

```python
from amrita_core.contexts import StateContext

# 自动生成会话 ID
state = StateContext()
print(state.session_id)  # 例如 "a1b2c3d4e5f6..."

# 显式会话 ID
state = StateContext(session_id="my_session")
print(state.session_id)  # "my_session"
```

> **迁移**：不要创建 `StateContext` 再传给 `ChatObject(context=...)`，
> 直接传 `session_id` 并在之后设置 `data`：
>
> ```python
> from amrita_core.chatmanager import ChatObject
>
> chat = ChatObject(user_input="...", session_id="my_session")
> chat.data = MemoryModel(messages=[...])  # 替代 state.memory
> ```
