# ModelPreset

The ModelPreset class defines the preset configuration for AI models.

## Properties

- `model` (str): Name of the AI model (e.g. gpt-3.5-turbo)
- `name` (str): Identifier name for current preset, defaults to "default"
- `base_url` (str): Base address of API service (uses OpenAI default if empty)
- `api_key` (str): Key required to access API
- `protocol` (str): Protocol adapter type, defaults to `"__main__"` (OpenAI-compatible adapter)
- `rate` ([RateConfig](RateConfig.md) | None): Pricing snapshot used for cost accounting. Copied into every [BillingRecord](BillingRecord.md) produced while this preset is active
- `max_context` (int | None): Input token budget of the model. Together with `max_output` it forms the attention window. Falls back to `LLMConfig.session_tokens_windows` when unset
- `max_output` (int | None): Default `28000`. Tokens reserved for the response, i.e. the `max_tokens` request parameter. The model owns this number. `LLMConfig.max_tokens` is the last-resort fallback, used only when this is explicitly set to `None`
- `config` (`ModelConfig`): Model configuration object
- `thinking_config` ([ThinkingConfig](ThinkingConfig.md) | None): Thinking/reasoning configuration for models that support it (e.g., OpenAI o1, Anthropic extended thinking)
- `extra` (dict[str, Any]): Extra configuration items

## Methods

- `load(path: Path)`: Load model preset configuration from the specified path
- `save(path: Path)`: Save current preset configuration to the specified path

## Resolving the Window

Two module-level helpers resolve a preset field against the global config, so callers never have to branch on `None` themselves:

```python
from amrita_core.types.preset import resolve_max_context, resolve_max_output

window = resolve_max_context(
    preset, config
)  # preset.max_context or config.llm.session_tokens_windows
budget = resolve_max_output(
    preset, config
)  # preset.max_output or config.llm.max_tokens
```

The model adapters use `resolve_max_output` for the `max_tokens` request parameter, and `ContextCompactor` uses `resolve_max_context` for the compaction threshold.

> Because `rate.input` / `rate.output` are `Decimal`, `model_dump()` returns `Decimal` objects. `save()` therefore writes `model_dump(mode="json")`; do the same in your own serialization code.

## Description

The ModelPreset class inherits from BaseModel and is used to encapsulate complete configuration information for AI models. It not only includes basic model parameters but also provides functionality to load and save configuration files, facilitating management and reuse of different model configurations.
