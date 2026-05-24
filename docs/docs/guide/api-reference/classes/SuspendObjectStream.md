# SuspendObjectStream

> **Migrated to AmritaSense**. `amrita_core.streaming` is now a deprecated wrapper.

`SuspendObjectStream` is a producer-single-consumer architecture built on top of AnyIO memory object streams, with built-in suspend/resume and streaming response capabilities.

**Full API Documentation**: [SuspendObjectStream — AmritaSense](https://sense.amritabot.com/reference/api/suspend-object-stream)

## Migration

```python
# Old (deprecated)
from amrita_core.streaming import SuspendObjectStream

# New
from amrita_sense.streaming import SuspendObjectStream
```

## Usage in AmritaCore

ChatObject inherits from `SuspendObjectStream[RESPONSE_TYPE]`. All streaming interaction methods come from this base class:

| Method                     | Purpose                                      |
| -------------------------- | -------------------------------------------- |
| `yield_response()`         | Send response to queue or callback           |
| `get_response_generator()` | Asynchronously iterate over response stream  |
| `set_callback_func()`      | Set a response callback                      |
| `wait_to_suspend()`        | Wait for suspension externally               |
| `resume()`                 | Resume execution                             |
| `@suspend`                 | Decorator for suspendable methods            |
| `@suspend_with_tag(tag)`   | Decorator for suspendable methods with a tag |

> **Note**: `callback` and `async for` iteration are **mutually exclusive** — only one method can be used to consume the response stream per instance.
