# Security Mechanisms

## Cookie Security Detection

AmritaCore can detect sensitive cookie values in model responses and terminate
the session to prevent data leakage:

- **Activation**: `config.cookie.enable_cookie = True`
- **Detection**: responses are scanned for configured cookie values
- **Response**: on match, the session terminates with a generic error message

```python
from amrita_core.config import AmritaConfig

config = AmritaConfig()
config.cookie.enable_cookie = True
# configure cookie values to protect
```

## Prompt Injection Considerations

Tool results and peer messages enter the model context as text. Treat them as
untrusted:

- **Built-in strategies** store tool results in `ToolResult` pairs; the
  XML-rendering style of the deprecated `HybridReActAgentStrategy` carried
  higher injection risk (plain-text results).
- **Peer messages** (`send_to_producer`) are appended with the `[peer message]`
  marker — design your system prompt to treat that marker as data, not
  instructions.
- **Custom tools**: validate tool outputs before returning them if they come
  from external sources.

## Sensitive Data in Contexts

- Strategies hold `chat_object` as a lifecycle handle — do not log it
- `StateContext` (legacy accessor) exposes session id / memory / ability —
  treat it as sensitive when serializing

## Template Safety

Jinja2 template variables must not collide with built-in names
(`train`, `memory`, `chatobj`, `config`) — collisions raise `TypeError`
(see [Jinja2 Templates](agent-engineering/jinja2-templates.md)).

## Session Isolation

Memory is keyed by `session_id`; different ids are isolated. Use unique,
non-guessable session ids for multi-tenant deployments.
