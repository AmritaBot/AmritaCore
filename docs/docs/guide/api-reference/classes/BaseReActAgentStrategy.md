# BaseReActAgentStrategy

`BaseReActAgentStrategy` is an abstract base class for ReAct agent strategies that implements the template method pattern for unified execution flow.

This class provides shared functionality for ReAct-style agents including tool calling orchestration, reasoning message generation, loop detection, and common error handling patterns.

## Inheritance

- Extends: [AgentStrategy](AgentStrategy.md)
- Abstract Base Class: Yes

## Properties

- `agent_last_step` (str | None): Tracks the last reasoning step or action taken
- `call_count` (int): Counter for tool call iterations
- `tools` (list[Any]): List of available tools for the agent
- `origin_msg` (str): Original user message content
- `origin_instruction` (str): System instruction from training context
- `reasoning_pc` (int): Reasoning process counter for loop detection
- `_suggested_stop` (bool): Flag indicating whether to switch tool_choice to auto mode

## Constructor Parameters

- `ctx` ([StrategyContext](StrategyContext.md)): Strategy context containing chat_object, configuration, and message context

## Template Method Pattern

`BaseReActAgentStrategy` implements the template method pattern where the common execution flow is defined in `_execute_tool_loop()`, but strategy-specific behaviors are delegated to abstract methods:

### Abstract Methods (Must be implemented by subclasses)

#### \_append_tool_result_to_context()

Append tool result to context (strategy-specific).

**Parameters**:

- `tool_call` ([ToolCall](ToolCall.md)): The tool call object
- `func_response` (str): The function execution result
- `response_msg` ([UniResponse](UniResponse.md)): The original response message

#### \_handle_error_append()

Handle appending error messages to context (strategy-specific).

**Parameters**:

- `function_name` (str): Name of the failed function
- `error_content` (str): Formatted error message to append
- `tool_call_id` (str): ID of the tool call
- `original_exception` (BaseException): The original exception object for type-based handling

#### \_append_reasoning()

Append reasoning content to context (strategy-specific).

**Parameters**:

- `response` ([UniResponse](UniResponse.md)): The response from tools_caller containing reasoning tool calls

### Concrete Methods (Can be overridden by subclasses)

#### \_build_stop_response()

Build the stop tool response message.

**Parameters**:

- `function_args` (dict[str, Any]): Arguments passed to the stop tool

**Returns**: str - The instruction message for final answer generation

#### \_check_and_handle_loop_reasoning()

Check if loop reasoning threshold has been exceeded and build prompt.

**Returns**: str | None - Loop detection prompt if threshold exceeded, None otherwise

#### \_notify_tool_calls()

Send tool call completion notifications to user.

**Parameters**:

- `result_msg_list` (list[[ToolResult](ToolResult.md)]): List of tool results to notify
- `function_name` (str): Name of the called function
- `tool_call_id` (str): ID of the tool call

#### \_handle_loop_reasoning_cleanup()

Clean up strategy-specific state when loop reasoning is detected.

**Parameters**:

- `prompt` (str): The loop detection prompt message

#### \_build_stop_response_and_append()

Build stop response and append to message list (strategy-specific).

**Parameters**:

- `function_args` (dict[str, Any]): Arguments passed to the stop tool
- `response_msg` ([UniResponse](UniResponse.md)): The original response message

## Usage

This class should not be instantiated directly. Instead, create subclasses that implement the required abstract methods:

```python
from amrita_core.builtins.agent import BaseReActAgentStrategy

class MyCustomReActStrategy(BaseReActAgentStrategy):
    async def _append_tool_result_to_context(self, tool_call, func_response, response_msg):
        # Implement strategy-specific tool result handling
        pass

    async def _handle_error_append(self, function_name, error_content, tool_call_id, original_exception):
        # Implement strategy-specific error handling
        pass

    async def _append_reasoning(self, response):
        # Implement strategy-specific reasoning handling
        pass

    @classmethod
    def get_category(cls):
        return "agent-mixed"
```

## Built-in Subclasses

- [ReActAgentStrategy](ReActAgentStrategy.md): Standard implementation with OpenAI-compatible ToolCall-ToolResult pairing
- [HybridReActAgentStrategy](HybridReActAgentStrategy.md): Specialized implementation for MoE architecture models using XML tags
