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

| Setting                                   | Default     | Effect                                                                       |
| ----------------------------------------- | ----------- | ---------------------------------------------------------------------------- |
| `function_config.agent_tool_call_limit`   | `10`        | Hard cap on tool rounds per run                                              |
| `function_config.agent_step_token_budget` | `-1`        | Per-Step prompt-token budget (`<= 0` = disabled/unlimited)                   |
| `builtin.tool_calling_mode`               | `"agent"`   | `"agent"` / `"rag"` / `"none"`                                               |
| `builtin.agent_thought_mode`              | `"chat"`    | `"reasoning"` / `"chat"` / `"reasoning-required"` / `"reasoning-optional"`   |
| `builtin.loop_reasoning_trigger`          | `5`         | Stall detection: N identical tool signatures → give up                       |
| `llm.context_strategy`                    | `"compact"` | How an oversized history is handled: `"compact"` / `"slide"` / `"none"`      |
| `llm.compaction_trigger_ratio`            | `0.9`       | Fraction of the attention window at which history management fires           |
| `llm.slide_target_ratio`                  | `0.7`       | Under `"slide"`, the fraction of the window history is trimmed down to       |
| `preset.max_context`                      | `None`      | Per-model input budget; falls back to `llm.session_tokens_windows` (64k)     |
| `preset.max_output`                       | `28000`     | Per-model response reservation; `llm.max_tokens` (10000) is the last resort  |
| `llm.memory_length_limit`                 | `200`       | Message-count fallback that fires even when no usage is reported (`0` = off) |
| `llm.enable_overflow_recovery`            | `True`      | Compact and retry once when the provider rejects an oversized request        |

## Presets

A `ModelPreset` bundles endpoint + model + `ThinkingConfig` + tools, and is
loaded from the data backend per session. `create_agent()` builds one from your
`base_url` / `api_key` / `model` arguments; advanced setups use
`MultiPresetManager` to serve different presets per session (see
[Data Layer](data.md)).

### The Attention Window Lives on the Preset

The input budget and the response reservation belong to the **model**, not to a
global setting:

```python
from amrita_core import ModelPreset

preset = ModelPreset(
    model="deepseek-chat",
    name="deepseek",
    api_key="sk-...",
    max_context=64_000,  # input budget
    max_output=8_000,  # tokens reserved for the response
)
```

`max_context` + `max_output` is the model's attention window — the equivalent of
Copilot's "reserved for response". `LLMConfig.session_tokens_windows` and
`LLMConfig.max_tokens` are only the fallbacks used when a preset leaves them
unset, so a model's real limit follows the model.

Two helpers resolve a preset field against the config so callers never branch on
`None` themselves:

```python
from amrita_core.types.preset import resolve_max_context, resolve_max_output

window = resolve_max_context(preset, config)
budget = resolve_max_output(preset, config)
```

The model adapters use `resolve_max_output` for the request's `max_tokens`, and
`ContextCompactor` uses `resolve_max_context` for the compaction threshold. That
is why the two settings in the table above are read as a pair: the window drives
the compaction trigger.

### Pricing

A preset may also carry a `rate`, a [`RateConfig`](../api-reference/classes/RateConfig.md)
holding the unit price. It is copied into every billing record produced while
the preset is active, so cost history stays readable after a price change. See
[Data Backend](data-backend.md) for where those records go.

## Next

[Event System](event.md) — hooks into the processing pipeline.
