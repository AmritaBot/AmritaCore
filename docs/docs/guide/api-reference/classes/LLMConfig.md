# LLMConfig

The LLMConfig class defines configuration parameters for LLM calls and memory management.

## Properties

- `require_tools` (bool): Default `False`. Whether to force at least one tool to be used per call
- `max_tokens` (int): Default `10000`. Last-resort fallback for the response output budget (must be `>= 1`). The number that reaches the provider normally comes from [`ModelPreset.max_output`](ModelPreset.md) (default `28000`); this is used only when a preset sets `max_output=None` explicitly
- `compaction_max_tokens` (int): Default `2048`. Output-token ceiling for the history-compaction summary call (must be `>= 0`; `0` lets the summary use the preset's own value). A reasoning model spends its output budget on thinking before it emits anything, so a summary that inherits a small `max_output` comes back empty and the fold silently does nothing
- `session_tokens_windows` (int): Default `65536` (64k). Fallback attention window used when the active preset does not declare `max_context` (must be `>= 1`)
- `llm_timeout` (int): Default `60`. API request timeout duration (seconds) (must be `>= 1`)
- `max_retries` (int): Default `3`. Maximum number of retries (must be `>= 0`; `0` disables retrying)
- `max_fallbacks` (int): Default `5`. Maximum number of preset fallbacks (must be `>= 1`; `0` would make every request fail immediately)
- `context_strategy` (Literal): Default `"compact"`. How history that outgrows the budget is handled — `"compact"`, `"slide"` or `"none"`. See [History Policies](#history-policies)
- `compaction_trigger_ratio` (float): Default `0.9`. Fraction of the attention window at which history management is forced (must be in `(0, 1]`). Kept below `1.0` to absorb the lag between the last measured prompt size and the next request's actual size
- `slide_target_ratio` (float): Default `0.7`. Fraction of the attention window that `"slide"` trims history down to (must be in `(0, 1]`; a validator rejects a value at or above `compaction_trigger_ratio`, since a trim that lands back on the trigger re-runs on every request)
- `memory_length_limit` (int): Default `200`. Message-count fallback that forces history management regardless of token accounting (must be `>= 0`; `0` disables the fallback)
- `enable_overflow_recovery` (bool): Default `True`. Whether to shrink the history and retry once when the provider rejects a request for exceeding the context window. The shrink follows `context_strategy`, like the between-turn path (ignored under `"none"`)
- `enable_multi_modal` (bool): Default `True`. Whether to enable multi-modal support (currently only supports image)

## Attention Window and History Policies

The attention window comes from the model, not from a global number. Each [`ModelPreset`](ModelPreset.md) can declare its own `max_context` (input budget) and `max_output` (response reservation); `session_tokens_windows` and `max_tokens` are only the fallbacks used when a preset leaves them unset. A model's real limit therefore follows the model.

History management fires on whichever trigger comes first:

- **Token trigger**: the prompt size the provider reported for the previous request reaches `compaction_trigger_ratio` × `max_context`. No local tokenizer is involved — the provider's own usage report is the measurement
- **Message-count fallback**: the history reaches `memory_length_limit` messages. This exists because the token trigger needs the provider to report usage; a gateway that reports none would otherwise let history grow without bound. Under `"slide"` this ceiling is also the trim target when no measurement is available

A typical agent message (including tool calls and their results) costs roughly 300 tokens, so a 64k window is around 200 messages. Set `memory_length_limit` to `0` only if every provider you use reports usage.

### History Policies

`context_strategy` picks what happens once a trigger fires:

| Value       | Behavior                                                                                                                                                                                                           |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `"compact"` | Folds the oldest prefix into an LLM summary stored on [`MemoryModel.abstract`](MemoryModel.md), rendered back into the system instruction by the train template. Costs one extra model call, but the gist survives |
| `"slide"`   | Drops the oldest messages outright, down to `slide_target_ratio` × `max_context`, or to `memory_length_limit` messages when no measurement is available. No extra call; the tail stays verbatim, but the dropped content is gone for good                                                 |
| `"none"`    | Leaves history untouched and unbounded, and lets the provider reject the request once the window is exceeded                                                                                                       |

`"slide"` estimates each message's share of the reported prompt size, so it needs no tokenizer either: the weights are normalized so they sum back to the measurement. It never cuts mid-turn and never strands a tool result whose declaring call it removed, so the trimmed payload still passes the gateway validator.

`"slide"` is the right choice when the early turns are disposable (a long tool-calling session) and a summary call per trim is too expensive. `"compact"` is the right choice when the early turns still carry decisions that later turns depend on.

## Description

The LLMConfig class inherits from BaseModel and is exposed as `AmritaConfig.llm`. It controls token limits, retry/fallback behavior, history management, and multi-modal support.

## Example

```python
from amrita_core.config import LLMConfig

llm_config = LLMConfig(
    context_strategy="compact",  # "compact" | "slide" | "none"
    compaction_trigger_ratio=0.85,  # Act once 85% of the window is in use
    slide_target_ratio=0.7,  # Under "slide", trim back down to 70%
    memory_length_limit=200,  # Message-count fallback
    enable_overflow_recovery=True,  # Shrink and retry on a provider overflow error
)
```
