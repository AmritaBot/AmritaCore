# StateContext

一个数据类，保存 `ChatObject` 会话的完整运行时状态。

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
