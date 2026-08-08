# Configuration

All runtime settings live in **`AmritaConfig`** — a single object you create
once and pass to `create_agent()` / `ChatObject` (or set globally).

## The Config Tree

| Field                                | Purpose                                                           |
| ------------------------------------ | ----------------------------------------------------------------- |
| `llm` (`LLMConfig`)                  | Model settings: stream, temperature, memory abstraction, thinking |
| `function_config` (`FunctionConfig`) | Tool calling: limit, minimal context, middle messages             |
| `builtin` (`BuiltinAgentConfig`)     | Agent behavior: tool calling mode, thought mode, stall trigger    |
| `cookie` (`CookieConfig`)            | Cookie security detection                                         |

## Global vs Per-Call

```python
from amrita_core import minimal_init
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig

config = AmritaConfig(
    function_config=FunctionConfig(agent_tool_call_limit=15),
    llm=LLMConfig(stream=True),
)
await minimal_init(config)  # global default

agent = create_agent(..., config=config)  # or per-agent
```

`get_config()` returns the global config; `set_config()` replaces it.

## Key Settings for Agent Behavior

| Setting                                   | Default   | Effect                                                      |
| ----------------------------------------- | --------- | ----------------------------------------------------------- |
| `function_config.agent_tool_call_limit`   | `10`      | Hard cap on tool rounds per run                             |
| `function_config.agent_step_token_budget` | `None`    | Per-Step prompt-token budget (stops the iteration loop)     |
| `builtin.tool_calling_mode`               | `"agent"` | `"agent"` / `"rag"` / `"none"`                              |
| `builtin.agent_thought_mode`              | —         | `"reasoning"` / `"reasoning-required"` (explicit reasoning) |
| `builtin.loop_reasoning_trigger`          | —         | Stall detection: N identical tool signatures → give up      |
| `llm.enable_memory_abstract`              | `True`    | Auto-summarize long history                                 |
| `llm.memory_abstract_threshold`           | `None`    | Prompt-token threshold for between-Step history compression |

## Presets

A `ModelPreset` bundles endpoint + model + `ThinkingConfig` + tools, and is
loaded from the data backend per session. `create_agent()` builds one from your
`base_url` / `api_key` / `model` arguments; advanced setups use
`MultiPresetManager` to serve different presets per session (see
[Data Layer](data.md)).

## Next

[Event System](event.md) — hooks into the processing pipeline.
