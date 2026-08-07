# Workflow Debugging

## Step Through the Interpreter

AmritaSense's `WorkflowInterpreter` supports `run_step_by()` — yield every
node execution instead of running to completion:

```python
async def debug(chat: ChatObject) -> None:
    interp = chat._interpreter
    async for result in interp.run_step_by():
        print(f"→ {result}")
```

Combine with [suspend points](suspend.md) to inspect state between nodes.

## Node Breakpoints

`@Node(tag=...)` tags double as suspend points. External code can
`wait_to_suspend(tag)` on the stream to pause exactly at a node of interest —
for example `"ChatObject::step_intro"` to stop at every Step boundary.

## Middleware

Wrap the entire workflow with `middleware` for coarse-grained control:

```python
async def trace_middleware(chat: ChatObject) -> None:
    print(f"[trace] start {chat.stream_id}")
    try:
        await chat._interpreter.run()
    finally:
        print(f"[trace] done {chat.stream_id}")


chat = ChatObject(..., middleware=trace_middleware)
```

## Common Inspection Points

| What to check      | Where                                         |
| ------------------ | --------------------------------------------- |
| Current Step state | `chat._di_loop.run_state` (`AgentRunState`)   |
| Strategy context   | `chat._di_loop.stg_ctx`                       |
| Message list       | `chat._di_working.context_wrap`               |
| Stream events      | the `get_response_generator()` metadata items |
| Session memory     | `chat._di_memory.memory`                      |

> In AmritaSense terms, `run_step_by()` and middleware are engine features —
> see [sense.amritabot.com](https://sense.amritabot.com) for the general
> debugging reference.
