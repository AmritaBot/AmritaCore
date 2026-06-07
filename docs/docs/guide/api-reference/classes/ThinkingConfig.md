# ThinkingConfig

The ThinkingConfig class configures thinking/reasoning capabilities for supported models (e.g., OpenAI o1 series, Anthropic Claude with extended thinking).

## Properties

- `thinking_type` (Literal["enabled", "disabled"] | None): Whether to enable thinking. Adds a `thinking.type` property to the API request (provider-specific). Default: None
- `enable_thinking` (bool | None): Whether to enable thinking via the `enable_thinking` request property (provider-specific). Default: None
- `thinking_effort` (str | None): Controls the thinking effort level. Model-dependent — typical values include `"minimal"`, `"low"`, `"medium"`, `"high"`, `"xhigh"`, or `"max"`. Default: `"high"`
- `content_mode` (Literal["never", "by-tool", "optional"]): Controls how `reasoning_content` is handled in message history:
  - `"never"`: Strip all reasoning content
  - `"by-tool"`: Keep reasoning only for assistant messages that include `tool_calls` (Anthropic requirement)
  - `"optional"`: Pass through reasoning content as-is (default)

## Description

The ThinkingConfig class inherits from BaseModel and provides granular control over model thinking/reasoning behavior. It is set on `ModelPreset.thinking_config` and used by adapters (OpenAIAdapter, AnthropicAdapter) to configure thinking-related request parameters.

When enabled, the model's reasoning process is exposed via:

- `UniResponse.reasoning_content` — the thinking/reasoning text
- `UniResponse.reasoning_signature` — Anthropic signature for round-tripping
- `Message.reasoning_content` — stored in conversation history
- `Message.reasoning_signature` — stored for Anthropic API round-tripping

## Example

```python
from amrita_core.types import ThinkingConfig, ModelPreset

# Enable extended thinking with Anthropic
preset = ModelPreset(
    model="claude-sonnet-4-20250514",
    name="thinking-claude",
    api_key="your-api-key",
    thinking_config=ThinkingConfig(
        thinking_type="enabled",
        thinking_effort="high",
        content_mode="by-tool",
    ),
)

# Enable reasoning with OpenAI o-series
preset_openai = ModelPreset(
    model="o3",
    name="thinking-o3",
    api_key="your-api-key",
    thinking_config=ThinkingConfig(
        thinking_effort="medium",
        content_mode="optional",
    ),
)
```
