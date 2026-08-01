# ReActAgentStrategy

`ReActAgentStrategy` 是在 RAG 和 Agent 模式下执行 agent 的策略。此策略实现 `"agent-mixed"` 类别。

## 属性

- `agent_last_step` (str | None)：agent 执行的上一步
- `call_count` (int)：到目前为止的工具调用次数
- `tools` (list[Any])：当前上下文的可用工具列表
- `origin_msg` (str)：原始用户消息内容

## 方法

### single_execute()

为 `"agent-mixed"` 类别策略执行单步 agent 操作。根据当前上下文和配置动态处理 RAG 和 Agent 模式。

**返回**：bool - 是否继续下一次执行

### get_category()

获取 agent 策略的类别。

**返回**：Literal["agent-mixed"]

## 策略类别：agent-mixed

`"agent-mixed"` 类别允许策略在同一执行框架内动态处理检索增强生成场景和标准迭代工具调用 agent。
