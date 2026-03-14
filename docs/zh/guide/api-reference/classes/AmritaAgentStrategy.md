# AmritaAgentStrategy

AmritaAgentStrategy 是用于在 RAG 和 Agent 模式下执行 agent 的策略。

该策略实现了 'agent-mixed' 类别，允许在同一执行框架内动态处理检索增强生成场景和标准迭代工具调用 agent。

## 属性

- `agent_last_step` (str | None): agent 执行的最后一步
- `call_count` (int): 到目前为止进行的工具调用次数
- `tools` (list[Any]): 当前上下文中可用的工具列表
- `origin_msg` (str): 原始用户消息内容

## 构造函数参数

- `ctx` ([StrategyContext](StrategyContext.md)): 包含 chat_object、配置和消息上下文的策略上下文

## 方法

### single_execute()

为 'agent-mixed' 类别策略执行单个 agent 步骤。

此方法根据当前上下文和配置动态处理 RAG 和 Agent 模式。它支持推理模式、工具调用和适当的错误处理。

**返回**: bool - 如果应继续下一次执行则返回 True，否则返回 False。

### _generate_reasoning_msg(original_msg, tools_ctx)

为 agent 的思维过程生成推理消息。

**参数**:
- `original_msg` (str): 原始用户消息
- `tools_ctx` (list[dict[str, Any]]): 可用工具的上下文

### _append_reasoning(response)

将推理结果附加到消息上下文中。

**参数**:
- `response` (UniResponse[None, list[ToolCall] | None]): 包含推理工具调用的响应

### get_category()

获取 agent 策略的类别。

**返回**: Literal["agent-mixed"] - 此策略实现了 'agent-mixed' 类别。

## 策略类别: agent-mixed

'agent-mixed' 类别允许策略在同一执行框架内动态处理检索增强生成场景和标准迭代工具调用 agent。这提供了灵活性，可以根据当前上下文和需求在运行时调整执行策略。

## 使用示例

```python
from amrita_core.agent.context import StrategyContext
from amrita_core.builtins.agent import AmritaAgentStrategy

# 创建策略上下文
ctx = StrategyContext(
    user_input="你能做什么？",
    original_context=message_context,
    chat_object=chat_obj
)

# 创建并使用策略
strategy = AmritaAgentStrategy(ctx)
should_continue = await strategy.single_execute()
```
