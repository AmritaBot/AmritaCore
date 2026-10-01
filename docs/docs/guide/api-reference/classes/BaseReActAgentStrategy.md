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

#### \_append_reasoning()

Append reasoning content to context (strategy-specific).

**Parameters**:

- `tool_call` (`ToolCall`): The tool call that requested the reasoning
- `reasoning_content` (`UniResponse[str, None]`): The reasoning response

### Concrete Methods (Can be overridden by subclasses)

#### \_append_tool_results_batch(response_msg, results)

Append one tool round to the context. Called once per round with **every**
result of that round.

The default implementation appends a single assistant message carrying all
`tool_calls` plus the provider's reasoning fields copied verbatim, followed by
one `ToolResult` per call in the model's original order. Override it to change
how a round is recorded; keep the calls of one round in a single assistant
message, because splitting them would drop the reasoning from all but one
message and leave the provider with a `tool_calls` message whose results are
missing.

**Parameters**:

- `response_msg` (`UniResponse`): The original response message
- `results` (list[tuple[`ToolCall`, str, BaseException | None]]): One entry per executed call, in the model's order

#### \_handle_error_append()

Handle appending error messages to context (strategy-specific).

**Parameters**:

- `function_name` (str): Name of the failed function
- `error_content` (str): Formatted error message to append
- `tool_call_id` (str): ID of the tool call
- `original_exception` (BaseException): The original exception object for type-based handling

#### \_is_native_thinking_enabled()

Check whether the model preset has native thinking enabled.

Native thinking (Claude Extended Thinking, OpenAI o-series, etc.) may not support forced `tool_choice`. When enabled, `_resolve_tool_choice()` automatically downgrades forced values to avoid provider errors.

**Returns**: bool - True if the preset has native thinking enabled

#### \_resolve_tool_choice(desired: ToolChoice) -> ToolChoice

Resolve the _actual_ `tool_choice` to send to the provider.

When native thinking is enabled the provider may reject forced values (`"required"` or a specific tool schema). In that case falls back to `"auto"` and relies on prompt instructions to control tool calling behaviour.

**Parameters**:

- `desired` (`ToolChoice`): The desired tool_choice value

**Returns**: ToolChoice - The actual tool_choice value to send

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

- `result_msg_list` (list[`ToolResult`]): List of tool results to notify
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
- `response_msg` (`UniResponse`): The original response message

## Usage

This class should not be instantiated directly. Instead, create subclasses that implement the required abstract methods:

```python
from amrita_core.builtins.agent import BaseReActAgentStrategy


class MyCustomReActStrategy(BaseReActAgentStrategy):
    async def _append_reasoning(self, tool_call, reasoning_content):
        # The only required override: record the reasoning your own way.
        ...

    @classmethod
    def get_category(cls):
        return "agent-mixed"
```

`_append_tool_results_batch` and `_handle_error_append` already have working
defaults; override them only when you want a different way of recording tool
rounds.

## Built-in Subclasses

- [ReActAgentStrategy](ReActAgentStrategy.md): Standard implementation with OpenAI-compatible ToolCall-ToolResult pairing
