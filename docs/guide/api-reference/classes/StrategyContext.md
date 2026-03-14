# StrategyContext

The StrategyContext class provides the execution context for agent strategies.

This dataclass contains all the necessary information that an agent strategy needs to execute its workflow, including the user input, message context, and chat object reference.

## Properties

- `user_input` (USER_INPUT): The input from the user
- `original_context` (SendMessageWrap): The original message context containing system message, memory, and user query
- `chat_object` (ChatObject): Reference to the chat object for yielding responses and managing conversation flow

## Constructor Parameters

- `user_input` (USER_INPUT): Input from the user
- `original_context` (SendMessageWrap): Original message context
- `chat_object` (ChatObject): Chat object reference

## Methods

### get_original_context()

Get the original message context.

**Returns**: [SendMessageWrap](SendMessageWrap.md) - The original message context

### get_user_input()

Get the user input.

**Returns**: USER_INPUT - The user input

## Usage Example

```python
from amrita_core.agent.context import StrategyContext

# Create strategy context
ctx = StrategyContext(
    user_input="What can you do?",
    original_context=message_context,
    chat_object=chat_obj
)

# Access context properties
user_msg = ctx.get_user_input()
message_context = ctx.get_original_context()
```