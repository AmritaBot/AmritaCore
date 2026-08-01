# NoActionAgentStrategy

`NoActionAgentStrategy` is a simple workflow strategy that performs no action. It can be used to give up the tool calling process when needed.

## Inheritance

- Extends: [AgentStrategy](AgentStrategy.md)
- Category: `"workflow"`

## Constructor Parameters

- `ctx` ([StrategyContext](StrategyContext.md)): Strategy context containing chat_object, configuration, and message context

## Methods

### run()

No-action implementation that returns immediately without performing any operations.

**Returns**: None

### on_exception()

No-action exception handler that returns immediately without performing any operations.

**Parameters**:

- `exc` (BaseException): The exception that occurred

**Returns**: None

## Usage Example

```python
import asyncio
from amrita_core import create_agent, minimal_init
from amrita_core.builtins.agent import NoActionAgentStrategy

async def use_no_action_strategy():
    # Initialize AmritaCore
    await minimal_init()

    # Create agent with no-action strategy to skip tool execution
    agent = create_agent(
        url="https://api.example.com",
        key="your-api-key",
        strategy=NoActionAgentStrategy
    )

    # Use the agent - it will respond directly without calling tools
    chat = agent.get_chatobject("Just respond to this query directly")
    async with chat.begin():
        response = await chat.full_response()
        await chat  # Wait for the task to finish before exiting
```

## When to Use

Use `NoActionAgentStrategy` when:

- You want to skip tool execution entirely
- You need a simple direct response without any tool calling logic
- You're implementing conditional logic where tool calling should be bypassed in certain scenarios
- You need a placeholder strategy for testing or debugging purposes
