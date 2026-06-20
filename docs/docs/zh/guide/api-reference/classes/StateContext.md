# StateContext

保存 `ChatObject` 会话完整运行时状态的数据类。

## 描述

`StateContext` 是由 `ChatObject` 在执行期间创建和管理的运行时状态容器。它持有会话 ID、对话记忆和能力上下文。

## 字段

- `session_id` (str): 会话的唯一标识符。如果未提供，则自动生成为 UUID 十六进制字符串
- `memory` ([MemoryModel](MemoryModel.md)): 对话记忆模型
- `ability` ([AbilityContext](AbilityContext.md)): 能力上下文（工具、预设、MCP 客户端）
- `extra` (dict[str, Any]): 额外的自定义数据

## 用法

```python
from amrita_core.contexts import StateContext

# 自动生成会话 ID
state = StateContext()
print(state.session_id)  # 例如 "a1b2c3d4e5f6..."

# 使用显式会话 ID
state = StateContext(session_id="my_session")
print(state.session_id)  # "my_session"
```

## 注意

- `StateContext` 通常由 `ChatObject` 内部创建。仅在想要在多个 `ChatObject` 实例之间共享状态时（例如，在无后端持久化的多轮对话中）才需要直接创建一个。
