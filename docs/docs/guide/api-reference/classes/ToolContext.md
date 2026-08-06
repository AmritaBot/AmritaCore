# ToolContext

The ToolContext class provides context for custom tool execution in AmritaCore.

## Description

The ToolContext class is a dataclass that provides execution context for tools registered with `custom_run=True`. It contains the parameters passed to the tool and access to the current strategy execution context.

## Properties

- `data` (dict[str, Any]): The arguments passed to the tool by the LLM
- `ctx` ([StrategyContext](StrategyContext.md)): The current strategy execution context containing:
  - `user_input`: The original user input
  - `original_context`: The complete message context
  - `chat_object`: Reference to the [ChatObject](ChatObject.md) for yielding responses

## Usage

ToolContext is automatically passed to tools that are registered with the `custom_run=True` parameter:

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import ToolContext


@on_tools(data=my_tool_schema, custom_run=True)
async def my_custom_tool(ctx: ToolContext) -> str | None:
    # Access tool parameters
    param_value = ctx.data["param_name"]

    # Access the chat object to yield responses
    await ctx.ctx.chat_object.yield_response("Processing...")

    return f"Result: {param_value}"
```

This class ensures consistent access to both tool parameters and execution context across all custom tool implementations in AmritaCore.
