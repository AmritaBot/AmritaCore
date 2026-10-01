# Security Mechanisms

## Cookie Security Detection

AmritaCore can detect sensitive cookie values in model responses and terminate
the session to prevent data leakage:

- **Activation**: `config.cookie.enable_cookie = True` (the default)
- **Detection**: the model's answer **and** its reasoning are scanned for the
  configured cookie value. Reasoning is part of the model's output and reaches
  consumers as `reasoning_chunk` events, so scanning only the answer would let a
  model that quotes the cookie while thinking pass the check
- **Response**: on match, the run terminates with a generic error message and the
  event's response and reasoning are replaced, so the value is not stored on the
  response object or in the conversation history

The guard watches for **system-prompt leakage**: the canary lives inside the
system prompt, so any run that reproduces it has leaked system content into
model output, whether that came from a prompt-injection attempt or from the model
quoting the marker on its own. Firing on reasoning is deliberate — reasoning is
streamed to consumers just like the answer.

> Chunks already handed to a streaming consumer cannot be retracted. The error
> payload appended to the stream is what marks the run as failed, so consumers
> that render `reasoning_chunk` events should stop on an `error` event.

```python
from amrita_core.config import AmritaConfig

config = AmritaConfig()
config.cookie.enable_cookie = True
# configure cookie values to protect
```

## Prompt Injection Considerations

Tool results and peer messages enter the model context as text. Treat them as
untrusted:

- **Built-in strategies** store tool results in paired `ToolResult` messages
  rather than inlining them as plain text, keeping untrusted output out of the
  instruction-carrying text stream.
- **Peer messages** (`send_to_producer`) are appended with the `[peer message]`
  marker — design your system prompt to treat that marker as data, not
  instructions.
- **Custom tools**: validate tool outputs before returning them if they come
  from external sources.

## Sensitive Data in Contexts

- Strategies hold `chat_object` as a lifecycle handle — do not log it
- `MemoryModel` carries the full conversation plus billing records — treat it as
  sensitive when serializing

## Template Safety

Jinja2 template variables must not collide with built-in names
(`train`, `memory`, `chatobj`, `config`) — collisions raise `TypeError`
(see [Jinja2 Templates](agent-engineering/jinja2-templates.md)).

## Session Isolation

Memory is keyed by `session_id`; different ids are isolated. Use unique,
non-guessable session ids for multi-tenant deployments.
