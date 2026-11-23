# Workflow Debugging

## Step Through the Interpreter

AmritaSense's `WorkflowInterpreter` supports `run_step_by()` — yield every
node execution instead of running to completion:

```python
async def debug(chat: ChatObject) -> None:
    interp = chat._interpreter
    async for result in interp.run_step_by():
        print(f"-> {result}")
```

Combine with [suspend points](suspend.md) to inspect state between nodes.

## Node Breakpoints

`@Node(tag=...)` tags double as suspend points. External code can
`wait_to_suspend(tag)` on the stream to pause exactly at a node of interest —
for example `"ChatObject::step_intro"` to stop at every Step boundary.

The Step-boundary decisions are nodes too, so they take breakpoints directly:
`STEP_DECOMPOSE` (first-run decomposition), `STEP_BEGIN_NODE` /
`STEP_BEGIN_SIMPLE` / `STEP_BEGIN_BOUNDARY` (Step selection),
`STEP_PLAN_STATUS` (plan snapshot injection) and `STEP_SUMMARY` (Step
teardown).

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

## Panic Rescue: Step Into the REPL (Sense 1.2.0)

Some failures happen only once, on-site: a node raises something nobody
expected, the whole conversation dies, and all you keep is a traceback. Where
the pointer stopped, what was still on the return stack, what the context
stack held — all of it is unwound along with the exception.

Sense 1.2.0's `RESCUE_ON_PANIC` keeps those few seconds before the throw: a
panic no longer unwinds straight away, it stops at the crash site and opens an
`(sdb)` session.

> Requires `amrita-sense >= 1.2.0`. On 1.1.x the flag does not exist and setting it has no effect.

### Enable it

```python
from amrita_sense._unsafe import __flags__

__flags__.RESCUE_ON_PANIC = True
```

It is an unsafe flag and can be toggled at runtime, but treat it as start-up
configuration.

### Two paths

| Condition                            | Behaviour                                                                      |
| ------------------------------------ | ------------------------------------------------------------------------------ |
| stdin is an interactive terminal     | opens `(sdb)` in-process and blocks until you `q` / `k` / EOF                   |
| no terminal (bot process, CI, pipe)  | re-raises immediately with a `PanicReport` on `__sdb_report__`, plus a 3.11+ note |

The TTY check is more than `isatty()`: the process must own the terminal's
foreground process group and `TERM` must not be `dumb`. Two environment
variables override it:

```bash
SDB_REPL_DISABLE=1    # never enter (production guard, highest priority)
SDB_REPL_FORCE=1      # always enter (tests, manual triage)
SDB_REPL_TIMEOUT=300  # seconds to wait for input; 0 disables the timeout
```

Either path preserves the exception type. Rescue keeps the scene, it does not
swallow the failure.

### Catching it from Core

Processes like AmritaBot have no terminal, so rescue takes the `PanicReport`
branch. Persist the report — it is worth far more than a traceback scrolled
away in the process log:

```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def run_chat(chat: ChatObject) -> None:
    try:
        await chat.async_run()
    except Exception as exc:
        report = getattr(exc, "__sdb_report__", None)
        if report is not None:
            logger.error(report.summary())
            dump = Path("/var/log/amrita/panic")
            dump.mkdir(parents=True, exist_ok=True)
            (dump / f"{chat.stream_id}.txt").write_text(
                report.to_text(), encoding="utf-8"
            )
        raise
```

`summary()` is a single log-safe line (panic type, message, pc, flags);
`to_text()` carries the disassembly, backtrace and context stack and belongs
in its own file.

### What to do at the site

| Command                | When to use it                                                          |
| ---------------------- | ----------------------------------------------------------------------- |
| `bt` / `x` / `i r`     | See where it broke: call chain, current-segment disassembly, registers   |
| `s`                    | Re-run the panicking node (panic state is cleared before execution)      |
| `skip`                 | Skip the panicking node: pointer moves, stack does not                   |
| `suppress`             | End the rescue and let `run()` return normally                           |
| `suppress continue`    | Skip the failed node, then run the rest to completion                    |
| `undo`                 | Restore pc / return stack / flags / panic as the debugger sees them      |
| `py`                   | Real Python console; top-level `await` runs on the interpreter's loop    |
| `q` / `k`              | Leave and re-raise the original exception (`k` also closes the scope)    |

Boundaries worth remembering:

- `suppress` is the only path that hides the failure from the caller. It
  leaves a `panic suppressed by operator` warning, sets
  `inter.panic_suppressed`, and `inter.get_exception()` still answers where
  the run broke.
- A second panic during `suppress continue` is never swallowed; the command
  reports it and keeps the scene in the session.
- `undo` is not an execution rollback: nodes already run are not re-run and
  business side effects are not reverted.
- If `skip` jumps over the last node, rescue tells you the workflow already
  ended; `s` / `c` are refused rather than restarting from `[0]`.
- Rescue waits 300 seconds by default. If a production process must never
  block, set `SDB_REPL_DISABLE=1`.
- Code that drives `run_step_by()` directly does not trigger rescue
  automatically; call `rescue_on_panic()` yourself.
