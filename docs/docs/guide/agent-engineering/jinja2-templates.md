# Jinja2 Templates

The system (train) message is rendered through a **Jinja2 template** before
every request. This is how you inject memory, config and dynamic context into
the system prompt.

## Template Context

The template receives these variables:

| Variable      | Meaning                                    |
| ------------- | ------------------------------------------ |
| `train`       | The raw train message                      |
| `memory`      | The session `MemoryModel` (messages, etc.) |
| `chatobj`     | The current `ChatObject`                   |
| `config`      | The runtime `AmritaConfig`                 |
| `jinja2_vars` | Your custom variables (merged in)          |

```jinja2
You are a helpful assistant.
Today is {{ memory.metadata.today }}.
User prefers: {{ jinja2_vars.user_language }}
```

Pass custom variables via `ChatObject(..., jinja2_vars={...})` or
`agent.get_chatobject(..., jinja2_vars={...})`.

## Variable Naming Safety

**You CANNOT use keys that match built-in variable names**
(`train`, `memory`, `chatobj`, `config`) in `jinja2_vars` — Python would
receive duplicate keyword arguments and raise `TypeError`. Pick any other name.

## Best Practices

- Keep the template small; push instructions into it, not whole conversations
- Use the `config` variable to toggle behavior per deployment
- Render-time errors surface immediately — validate templates with the
  [workflow debugger](../advanced/workflow-debugging.md) before shipping

## Next

[Troubleshooting](troubleshooting.md) — the common failure modes and fixes.
