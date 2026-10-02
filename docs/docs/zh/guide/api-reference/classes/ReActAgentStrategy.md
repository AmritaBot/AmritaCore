# ReActAgentStrategy

`ReActAgentStrategy` 是在 RAG 和 Agent 模式下执行 agent 的策略。此策略实现 `"agent-mixed"` 类别，可在同一执行框架内动态处理检索增强生成场景与标准迭代式工具调用
agent。

## 属性

- `agent_last_step` (str | None)：agent 执行的上一步
- `call_count` (int)：到目前为止的工具调用次数
- `tools` (list[Any])：当前上下文的可用工具列表
- `origin_msg` (str)：原始用户消息内容

## 构造函数参数

- `ctx` ([StrategyContext](StrategyContext.md))：策略上下文，包含 chat_object、配置与消息上下文

## 方法

### single_execute()

为 `"agent-mixed"` 类别策略执行单步 agent 操作。

该方法根据当前上下文与配置动态处理 RAG 与 Agent 两种模式，支持推理模式、工具调用
与相应的错误处理。

**返回**：bool - 应继续下一次执行则返回 `True`，应停止则返回 `False`。

### `_generate_reasoning_msg(original_msg, tools_ctx)`

为 agent 的思考过程生成一条推理消息。

**参数**：

- `original_msg` (str)：原始用户消息
- `tools_ctx` (list[dict[str, Any]])：可用工具的上下文

### `_append_reasoning(response)`

把推理结果追加到消息上下文。

**参数**：

- `response` (UniResponse[None, list[ToolCall] | None])：包含推理工具调用的响应

### get_category()

获取 agent 策略的类别。

**返回**：Literal["agent-mixed"] - 本策略实现 `"agent-mixed"` 类别。

## 策略类别：agent-mixed

`"agent-mixed"` 类别允许策略在同一执行框架内动态处理检索增强生成场景和标准迭代工
具调用 agent。这提供了在运行时根据当前上下文与需求调整执行策略的灵活性。

## 使用示例

```python
from amrita_core.agent.context import StrategyContext
from amrita_core.builtins.agent import ReActAgentStrategy

# 创建策略上下文
ctx = StrategyContext(
    user_input="What can you do?",
    original_context=message_context,
    chat_object=chat_obj,
)

# 创建并使用该策略
strategy = ReActAgentStrategy(ctx)
should_continue = await strategy.single_execute()
```
