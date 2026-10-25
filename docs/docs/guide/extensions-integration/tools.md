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

## Declaring Concurrency Safety

Several tool calls of one model response are scheduled in pools. `concurrency_safe`
is a registration-time declaration stored on `ToolData`, and defaults to `True`:

```python
@on_tools(WRITE_FILE_DEFINITION, concurrency_safe=False)
async def write_file(arguments: dict) -> str: ...
```

To decide per call, pass a callable instead:

```python
@on_tools(QUERY_DEFINITION, concurrency_safe=lambda args: args.get("op") == "read")
async def query(arguments: dict) -> str: ...
```

`@simple_tool` is a plain decorator and cannot carry this declaration, so a tool
registered that way is always treated as stateless and concurrency-safe. A tool
that needs to declare otherwise has to go through
`@on_tools(..., concurrency_safe=False)`.

`False` means calls of this tool run alone and act as a barrier between the calls
around them in the same round; a callable decides per call from its arguments and
must return a literal `True` to be treated as safe. Keep the default `True` only
when you are sure the tool never rewrites the parent session, shared files, or
other state that concurrent calls can observe — a wrong call here costs a race,
not just speed.

## Returning Images from a Tool

`custom_run` handlers may return blocks too, which is how a tool streams progress
and hands back a rendered result in the same call:

```python
from amrita_core.types import Content, ImageContent, ImageUrl, TextContent


async def render_chart(tool_ctx: ToolContext) -> list[Content]:
    await tool_ctx.ctx.io_stream.yield_response("Rendering...")
    png = await chart(tool_ctx.data["query"])
    return [
        TextContent(text="chart ready"),
        ImageContent(image_url=ImageUrl(url=png)),
    ]
```

Both handler shapes accept `TOOL_RESULT_CONTENT` (`str | list[Content]`). A
`list[Content]` is passed through; anything else is JSON-encoded into a string,
so a handler returning a `dict` or a number behaves exactly as before.

Returning `None` from a `custom_run` handler still yields
`"(this tool returned no content)"`.

Two rules worth knowing:

- **The protocol decides, not you.** Whether the image actually reaches the model
  depends on the adapter's `features.tool_result_multimodal`. On an adapter
  without it, the gateway replaces the block with a text notice on the outgoing
  copy — your stored history keeps the original block, so nothing is lost if a
  fallback later reaches a stronger protocol.
- **Keep a text part.** Include a `TextContent` with what the image shows. The
  text view (`content_text()` / `ToolResult.text`) is what logs, the `ERR:`
  check and history compaction see; a result that is nothing but an image
  collapses to `<image>` there, which is useless to all three.

### Text-only adapters

Chat Completions cannot carry an image inside a `tool` message — that is why
`openai` declares `tool_result_multimodal=False`. If your deployment is
OpenAI-only and the image matters, do not rely on the gateway: send it yourself
as a follow-up `user` message, or have the tool return a URL that the next turn
fetches.

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
