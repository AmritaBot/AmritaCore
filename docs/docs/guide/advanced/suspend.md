# Suspend & Resume

## The Mechanism

Every `ChatObject` owns a `SuspendObjectStream` (in AmritaSense terms, the
workflow is the producer; your code is the consumer). The stream supports
**suspension**: the producer blocks at marked points until an external
`resume()`.

- `wait_to_suspend(tags)` — request the producer to block at tagged break points
- `resume()` — release it
- `@Node(SuspendEnum.X)` tags double as break points (e.g. `STEP_INTRO`,
  `MEMORY`, `COMPLE`)

```python
import asyncio


async def interactive(chat):
    stream = chat.io_stream
    suspend_task = asyncio.create_task(stream.wait_to_suspend("ChatObject::step_intro"))
    run_task = asyncio.create_task(chat.begin())
    await suspend_task  # producer is now paused at a Step boundary
    # ... inspect or inject ...
    stream.resume()  # let the agent continue
    await run_task
```

> Core recaps the Sense mechanics here; the full API is at
> [sense.amritabot.com — SuspendObjectStream](https://sense.amritabot.com/reference/api/suspend-object-stream).

## The Bidirectional Stream

The stream has **two independent channels**:

| Direction   | Producer API                        | Consumer API                                    |
| ----------- | ----------------------------------- | ----------------------------------------------- |
| Agent → You | `yield_response()`, `push_object()` | `get_response_generator()`                      |
| You → Agent | `get_producer_input_generator()`    | `send_to_producer()`, `send_done_to_producer()` |

### Peer → Agent Injection at Step Boundaries

Messages pushed with `send_to_producer()` are drained by the strategy at the
next Step boundary (`intro_step`) and appended to the conversation context as
`[peer message]` user messages:

- pushed **before** a Step starts → consumed at that boundary
- pushed **while** the agent works → queued until the next boundary
- pushed **after** the run → dropped (channel closed)

This enables human-in-the-loop feedback, external context injection, and
streaming inputs. See [Streaming](../tutorials/streaming.md) for the practical
usage.

## Rules

- One consumer per direction: generator _or_ callback (not both)
- After `set_queue_done()`, further `yield_response` raises `StreamStateError`
- After `send_done_to_producer()`, further `send_to_producer` fails fast —
  no blocking on the queue timeout

## Next

[The Step Loop](step-loop.md) — the built-in step-driven ReAct loop.
