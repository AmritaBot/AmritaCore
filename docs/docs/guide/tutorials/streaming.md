# 3. Streaming and Callbacks

## Goal of This Chapter

See your agent's output as it is produced — and read the structured events
hiding inside the stream. By the end you will be able to:

- Consume the stream with an async generator (pull) or a callback (push)
- Tell plain text chunks from `MessageWithMetadata` events
- Push messages _back_ to the agent through the reverse channel

## Concepts at a Glance (introduced only when needed)

- **`SuspendObjectStream`**: the bidirectional channel every `ChatObject` owns.
  The workflow writes into it; your code reads from it.
- **`MessageWithMetadata`**: a structured event (step boundary, tool call,
  reasoning chunk) that travels alongside plain text.

## 1. Stream the Response

Every `ChatObject` exposes `chat.io_stream` — a `SuspendObjectStream`. In
AmritaSense terms, the workflow is the _producer_ and your code is the
_consumer_; you read the response with an async generator:

```python
async with chat.begin():
    async for msg in chat.io_stream.get_response_generator():
        print(msg, end="", flush=True)
```

## 2. Two Kinds of Items

The stream carries **two** item types:

| Item                  | Meaning                                                          |
| --------------------- | ---------------------------------------------------------------- |
| `str`                 | A plain text chunk (token-by-token)                              |
| `MessageWithMetadata` | Structured events: step boundaries, tool calls, reasoning chunks |

```python
async with chat.begin():
    async for msg in chat.io_stream.get_response_generator():
        if isinstance(msg, str):
            print(msg, end="", flush=True)
        else:
            content = getattr(msg, "content", None)
            meta = getattr(msg, "metadata", None)
            if content:
                print(f"\n[{meta}] {content}", flush=True)
```

> **Do not concatenate every item.** A `str` chunk and a reasoning chunk are
> different things: calling `msg.get_content()` on both and joining the results
> folds the model's thinking into the answer. Branch on the type (or on
> `metadata["type"]`) as above. `chat.full_response()` already does this for
> you and returns the answer alone.

### Common metadata types

| `type`            | `extra_type`         | Emitted when                                                 |
| ----------------- | -------------------- | ------------------------------------------------------------ |
| `step`            | `decompose`          | The strategy decides simple vs DAG plan                      |
| `step`            | `intro` / `leave`    | A Step starts / ends (with summary)                          |
| `step`            | `stall` / `compress` | Stall detected / history compressed                          |
| `function_call`   | —                    | A tool starts (`is_done=False`) or finishes (`is_done=True`) |
| `reasoning_chunk` | `cot_chunk`          | Thinking-mode reasoning streamed                             |

> `step` metadata only exists while the **step-loop workflow** is active
> (`get_chatobject(..., workflow=_step_workflow_rendered)`); the default
> simple-chat workflow never emits it.

## 3. Callback-Based Consumption

Prefer push over pull? Register a callback instead of reading the generator:

```python
from amrita_core import SuspendObjectStream

stream = SuspendObjectStream(callback=on_chunk)
```

> Only one consumption mode is allowed per stream — generator _or_ callback.

## 4. The Reverse Channel (Peer → Agent)

`SuspendObjectStream` is **bidirectional**. The consumer can push messages back
to the producer with `send_to_producer()`; the agent drains them at the next
Step boundary and appends them to the conversation context:

```python
await chat.io_stream.send_to_producer(
    "IMPORTANT: end your final answer with the exact line: [peer-acked]"
)
```

- Messages pushed **before a Step starts** are consumed at that boundary.
- Messages pushed **while the agent is working** are picked up at the next Step.
- Messages pushed **after the run finishes** are dropped (channel closed).

> **A Step boundary is required.** Peer messages are drained in `intro_step`,
> which only the native step workflow reaches. Under the default simple-chat
> pipeline they are dropped without notice, so pass
> `get_chatobject(..., workflow=_step_workflow_rendered)` when you need the
> reverse channel.

This is the foundation for human-in-the-loop, tool feedback and streaming
inputs. See [Suspend/Resume](../advanced/suspend.md) for the full picture.

## What Just Happened

- The stream is pull-based (`get_response_generator`) or push-based (callback)
- Structured metadata travels alongside plain text
- The reverse channel lets you inject context at Step boundaries

## Next

[4. Events and Hooks](event-hooks.md) — intercept the pipeline programmatically.
