# Custom Tools — Advanced Patterns

## Goal of This Chapter

Go beyond the decorators. By the end you will be able to:

- Register tools manually with a `ToolsManager` (session-scoped control)
- Use `custom_run` mode to reach the framework from inside a tool
- Apply the full JSON Schema constraint set

> **Where is the basics?** The tool concept, the `@simple_tool` / `@on_tools`
> decorators and the execution path live in
> [Tool System (concepts)](../concepts/tool.md) and
> [Tutorial 2](../tutorials/tools.md). This page only covers what they do not.

## Manual Registration with `ToolsManager`

Decorators register into the global container. For session-scoped control,
register into a manager instance yourself:

```python
from amrita_core.tools.manager import MultiToolsManager
from amrita_core.tools.models import ToolData, ToolFunctionSchema

manager = MultiToolsManager()
manager.register_tool(
    ToolData(
        data=ToolFunctionSchema(function=STATUS_DEFINITION, strict=True),
        func=report_progress,
        custom_run=True,
    )
)
# pass the manager as the session's ability.tools (see Data Layer)
```

`MultiToolsManager` holds several named managers; a session resolves the one
assigned to it. `register_tool` rejects a duplicate tool name, and
`disable_tool` / `enable_tool` hide one without unregistering it.

## `custom_run` — Tools with Framework Access

When a tool needs the framework (streaming, session state), use `custom_run`:
the handler receives a `ToolContext` instead of a bare dict.

```python
from amrita_core import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
    ToolContext,
)

STATUS_DEFINITION = FunctionDefinitionSchema(
    name="report_progress",
    description="Report the agent's current progress to the user",
    parameters=FunctionParametersSchema(type="object", properties={}),
)


@on_tools(STATUS_DEFINITION)
async def report_progress(tool_ctx: ToolContext) -> str:
    # tool_ctx.data  — validated arguments (dict)
    # tool_ctx.ctx   — the StrategyContext (config, io_stream, ...)
    stream = tool_ctx.ctx.io_stream
    await stream.yield_response("Working on it...")
    return "progress reported"
```

**How it works**: `custom_run` is an explicit flag on the registration
(`on_tools(..., custom_run=True)`), stored on `ToolData`. `call_tool()` reads
that flag — it does **not** infer the mode from the handler's signature, so a
`ToolContext` parameter on a tool registered without the flag would receive the
argument dict instead.

## Validation Constraints

`FunctionPropertySchema` supports the full JSON Schema constraint set:

- Numeric: `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`
- String: `minLength`, `maxLength`, `pattern`, `format`
- Array: `items`, `minItems`, `maxItems`, `uniqueItems`
- Object: `properties`, `required`, `additionalProperties`
- Special: `enum`, `const`, `default`
- Union: `type` as a list (manual schemas only)

Arguments are checked before your handler runs, by a validator compiled from
the schema itself, so an invalid call never reaches it — the model gets an
`ERR:` result instead. See
[Tool System (concepts)](../concepts/tool.md#schemas-and-validation) for the
projection/compilation split and the `validate_tool_arguments` switch.

## Tool Calling Mode

`config.builtin.tool_calling_mode` controls availability:

| Mode      | Behavior                              |
| --------- | ------------------------------------- |
| `"agent"` | Full tool calling with built-in tools |
| `"rag"`   | One retrieval round, then stop        |
| `"none"`  | No tools at all                       |

## Next

[MCP Servers](mcp-server.md) — expose MCP tools to the agent.
