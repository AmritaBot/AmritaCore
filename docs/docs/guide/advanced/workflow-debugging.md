# Workflow-Level Debugging

> AmritaCore's `ChatObject` is driven by a **workflow engine** (provided by [AmritaSense](https://sense.amritabot.com)) that executes the processing pipeline node by node — template rendering → memory limiting → LLM call → memory commit, etc. See [Workflow Engine](workflow-engine.md) for the full node chain.

**Note: This is an advanced feature. Most users don't need to touch the workflow directly — [events & hooks](../tutorials/event-hooks.md) cover most observation needs, and [suspend](suspend.md) covers production breakpoints.**

When you do need to debug at the workflow level — to understand which node is running, inspect internal state between steps, or inject custom logic into the pipeline — you have two AmritaCore-native approaches, neither of which requires learning a separate debugger API.

## Choosing Your Approach

| What you want to do                                                        | Use                                                                                    |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Observe pipeline activity (logging, auditing, alerts)                      | [Events & Hooks](../tutorials/event-hooks.md)                                          |
| Pause execution at specific points, inspect or modify state, then resume   | [Suspend & Resume](suspend.md)                                                         |
| Wrap the entire workflow — see every step, time each node, trap errors     | [Middleware Injection](#middleware-injection)                                          |
| Insert custom inspection logic at a specific point in the pipeline         | [Archived Nodes Injection](#archived-nodes-injection)                                  |
| Step through node-by-node in a REPL, set breakpoints, recover from crashes | [AmritaSense REPL Debugger](https://sense.amritabot.com/guide/practice/repl-debugging) |

- **Events are for observing** — handlers run in parallel, never block the workflow.
- **Suspend is for production** — cooperative and tag-based, safe to ship.
- **Middleware and archived nodes are for development debugging** — they give you direct access to the workflow without needing to understand the AmritaSense runtime.

## Background: What Is the Workflow?

When you call `chat.begin()`, ChatObject hands its work to an internal **interpreter** that steps through a pre-compiled node graph:

```text
[JINJA2_RENDER] → [_limiting_memory] → [BUILD_MESSAGE] → [_pre_runner]
→ [_run_strategy] → [LLM_COMPLETION] → [_post_runner] → [COMMIT_MEMORY]
```

Each box is a **node** — a Python function tagged with a name like `"LLM_COMPLETION"` (these are the same tags used by `SuspendEnum`). The interpreter runs them in sequence, manages a call stack for sub-workflows (e.g. agent tool-call loops), and handles exceptions at node boundaries.

You can access the interpreter from any `ChatObject`:

```python
inter = chat._interpreter
```

The two debugging approaches below both work through this interpreter — but you don't need to call it directly. ChatObject's constructor accepts parameters that wire your debug code in.

## Middleware Injection

The `middleware` parameter is the most direct debugging hook: a single async function that **wraps the entire workflow execution**. Inside it, you can inspect anything on the `ChatObject` before, during, and after the run.

### Basic: Log Every Step

```python
import logging
from amrita_core import ChatObject

async def debug_middleware(chat_obj: ChatObject) -> None:
    """Log the start and end of every ChatObject execution."""
    logging.info("[debug] workflow starting — session=%s", chat_obj.session_id)
    try:
        await chat_obj._interpreter.run()
    finally:
        logging.info("[debug] workflow finished")

chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Hello!",
    session_id="session_123",
    middleware=debug_middleware,
)
```

The key line is `await chat_obj._interpreter.run()` — your middleware is responsible for driving the interpreter. You own the lifecycle: you can add setup before it, teardown after it, or even choose not to run it at all.

### Advanced: Inspect State Between Steps

Because the interpreter can also run **step by step** via `run_step_by()`, a middleware can inspect state after every single node:

```python
async def step_by_step_middleware(chat_obj: ChatObject) -> None:
    """Run the workflow one node at a time, printing state after each."""
    inter = chat_obj._interpreter
    async for _ in inter.run_step_by():
        node = inter.get_graph().calc.find_addr_safe(inter._pointer.base_addr)
        tag = getattr(node, 'tag', '<unknown>')
        depth = len(inter._ret_addr_stack)
        print(f"  ✓ [{tag}]  stack_depth={depth}")

chat = ChatObject(
    ...,
    middleware=step_by_step_middleware,
)
```

Output during a run:

```
  ✓ [LOAD_STATE]  stack_depth=0
  ✓ [JINJA2_RENDER]  stack_depth=0
  ✓ [_limiting_memory]  stack_depth=0
  ✓ [LLM_COMPLETION]  stack_depth=0
  ✓ [_post_runner]  stack_depth=0
  ✓ [COMMIT_MEMORY]  stack_depth=0
```

This gives you a real-time trace of every node the interpreter visits, without needing the AmritaSense debugger at all.

### Error Trapping

Because your middleware owns the `run()` call, you can catch exceptions from any node:

```python
async def safe_middleware(chat_obj: ChatObject) -> None:
    try:
        await chat_obj._interpreter.run()
    except Exception as exc:
        logging.error("[debug] workflow crashed at node %s: %s",
                       chat_obj._interpreter._pointer, exc)
        # The interpreter preserves panic state — you can inspect it
        raise
```

## Archived Nodes Injection

Sometimes you don't want to wrap everything — you want to inject logic at a **specific point** in the pipeline. The `archived_nodes` parameter lets you append extra nodes to the end of the standard pipeline.

A node is simply an async function decorated with `@Node`. ChatObject's dependency injection system wires its parameters automatically, so your node receives the same context objects (`MemoryContext`, `WorkingState`, etc.) that built-in nodes use.

### Example: Dump State After Completion

```python
from amrita_sense import Node
from amrita_sense.instructions import ARCHIVED_NODES

@Node("debug_dump_state")
async def dump_state(self, working: WorkingState, memory: MemoryContext):
    """Dump internal state after the workflow finishes."""
    print("=== Debug Dump ===")
    print(f"Response: {working.response.content if working.response else 'none'}")
    print(f"Memory messages: {len(memory.memory.messages) if memory.memory else 0}")
    print(f"Tool calls: {len(working.tool_calls) if hasattr(working, 'tool_calls') else 0}")
    print("==================")

# Package as archived storage
debug_nodes = ARCHIVED_NODES(dump_state)

chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Hello!",
    session_id="session_123",
    archived_nodes=debug_nodes,
)
```

The `dump_state` node runs **after** the standard pipeline finishes, because `archived_nodes` are appended to the end. To inject at a different position, compose a custom workflow (see [Pre-composed Workflows](workflow-engine.md#pre-composed-workflows-v0-12-6)):

```python
from amrita_core.builtins.workflows import SIMPLE_CHAT
from amrita_sense import Node

@Node("pre_llm_inspection")
async def inspect_before_llm(self, working: WorkingState):
    print(f"[debug] About to call LLM — {len(working.messages)} messages prepared")

# Insert before LLM_COMPLETION: everything up to LLM → our node → LLM → the rest
# (this requires understanding the node chain; see Workflow Engine for the full graph)
```

### Node Parameters (DI)

Your node function can declare any parameter that built-in AmritaCore nodes use. The interpreter resolves them from ChatObject's DI context at runtime. Common ones:

| Parameter type        | What it gives you                        |
| --------------------- | ---------------------------------------- |
| `ChatObject` (`self`) | The ChatObject instance itself           |
| `WorkingState`        | Current response, tool calls, messages   |
| `MemoryContext`       | Memory model and message history         |
| `AbilityState`        | Config, preset, backends                 |
| `GeneralInput`        | User input, system prompt, template vars |

If you need a parameter not listed here, check `src/amrita_core/contexts.py` for all available DI types.

### Restrictions

- `workflow` and `archived_nodes` are **mutually exclusive** — providing both raises `ValueError`.
- Archived nodes are skipped during normal execution (they sit behind a jump instruction). To call one on demand from outside the workflow, you need `call_sub(interrupt=True)` — see [External Interrupt Calls](https://sense.amritabot.com/guide/advanced/external_interrupt) in the AmritaSense docs.

## Going Deeper: AmritaSense REPL Debugger

If middleware and archived nodes aren't enough — for example, you need **interactive step-by-step execution** in a Python REPL, **conditional breakpoints** on specific nodes, or **crash recovery** (skip a crashing node and continue) — AmritaSense provides a dedicated debugger module:

```python
from amrita_sense.debugger import step, cont, break_at_tag, inspect, list_nodes

inter = chat._interpreter

list_nodes(inter)                   # print every node in the graph
break_at_tag(inter, "LLM_COMPLETION")  # set a breakpoint
cont(inter)                         # run until breakpoint or end
inspect(inter)                      # full state dump
```

All functions are synchronous (no `await`) — callable directly in `python` or `ipython`. Breakpoints are injected via composite middleware and never modify the runtime core.

> **Full API & examples**: [REPL Debugging](https://sense.amritabot.com/guide/practice/repl-debugging) in the AmritaSense documentation.  
> **Security**: Set `REMOVE_DEBUGGER=true` in production to physically remove the debugger module — any import then raises `AttributeError`.

## Summary

| Approach       | AmritaCore API                        | AmritaSense knowledge required  | Best for                              |
| -------------- | ------------------------------------- | ------------------------------- | ------------------------------------- |
| Middleware     | `ChatObject(..., middleware=fn)`      | Minimal — just `_interpreter`   | Wrapping, timing, error trapping      |
| Archived nodes | `ChatObject(..., archived_nodes=...)` | Basic `@Node` + DI types        | Injecting at specific pipeline points |
| REPL debugger  | `from amrita_sense.debugger import *` | `WorkflowInterpreter` internals | Interactive stepping, breakpoints     |
