# ReActAgentStrategy

The ReActAgentStrategy is a strategy for executing an agent in RAG and Agent mode.

This strategy implements the 'agent-mixed' category, allowing it to dynamically handle both retrieval-augmented generation scenarios and standard iterative tool calling agents within the same execution framework.

## Properties

- `agent_last_step` (str | None): The last step executed by the agent
- `call_count` (int): The number of tool calls made so far
- `tools` (list[Any]): List of available tools for the current context
- `origin_msg` (str): The original user message content

## Constructor Parameters

- `ctx` ([StrategyContext](StrategyContext.md)): Strategy context containing chat_object, configuration, and message context

## Methods

### single_execute()

Execute a single agent step for the 'agent-mixed' category strategy.

This method handles both RAG and Agent modes dynamically based on the current context and configuration. It supports reasoning mode, tool calling, and proper error handling.

**Returns**: bool - True if should continue to next execution, False to stop.

### \_generate_reasoning_msg(original_msg, tools_ctx)

Generate a reasoning message for the agent's thought process.

**Parameters**:

- `original_msg` (str): The original user message
- `tools_ctx` (list[dict[str, Any]]): Context for available tools

### \_append_reasoning(response)

Append reasoning results to the message context.

**Parameters**:

- `response` (UniResponse[None, list[ToolCall] | None]): The response containing reasoning tool calls

### get_category()

Get the category of the agent strategy.

**Returns**: Literal["agent-mixed"] - This strategy implements the 'agent-mixed' category.

## Strategy Category: agent-mixed

The 'agent-mixed' category allows the strategy to dynamically handle both retrieval-augmented generation scenarios and standard iterative tool calling agents within the same execution framework. This provides flexibility to adapt the execution strategy during runtime based on the current context and requirements.

## Usage Example

```python
from amrita_core.agent.context import StrategyContext
from amrita_core.builtins.agent import ReActAgentStrategy

# Create strategy context
ctx = StrategyContext(
    user_input="What can you do?",
    original_context=message_context,
    chat_object=chat_obj
)

# Create and use the strategy
strategy = ReActAgentStrategy(ctx)
should_continue = await strategy.single_execute()
```
