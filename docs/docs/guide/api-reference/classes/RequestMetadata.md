# RequestMetadata

`RequestMetadata` captures per-request diagnostic information returned by every adapter call through `UniResponse.metadata`.

## Properties

- `request_id` (str): Auto-generated unique request ID (UUID4). Defaults to a new UUID if not provided.
- `original_request_id` (str | None): Original request ID returned by the LLM provider adapter (e.g., OpenAI's `_request_id`, Anthropic's `request_id`). `None` when unavailable.
- `model` (str): The model used for the request. Defaults to `"__NOT_GIVEN__"` when not available (e.g., streaming before the first chunk).
- `stop_sequence` (str | None): The stop sequence that terminated generation, if any.
- `stop_reason` (STOP_REASON | None): Why the generation stopped. One of:

  | Value             | Meaning                    |
  | ----------------- | -------------------------- |
  | `"end_turn"`      | Natural completion         |
  | `"max_tokens"`    | Hit max token limit        |
  | `"stop_sequence"` | Matched a stop sequence    |
  | `"tool_use"`      | Model called a tool        |
  | `"pause_turn"`    | Anthropic pause turn       |
  | `"refusal"`       | Content filtered / refused |

## Usage

```python
from amrita_core.types.response import RequestMetadata

# Accessed via UniResponse
response: UniResponse = ...
print(response.metadata.model)  # e.g. "gpt-4o"
print(response.metadata.stop_reason)  # e.g. "end_turn"
print(response.metadata.original_request_id)  # Provider's request ID
```

> **Note**: `extra="allow"` is configured, so provider-specific fields may appear in addition to the standard ones.
