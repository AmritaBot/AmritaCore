# LLMConfig

The LLMConfig class defines configuration parameters for LLM calls and memory management.

## Properties

- `require_tools` (bool): Default `False`. Whether to force at least one tool to be used per call
- `max_tokens` (int): Default `1000`. Maximum number of tokens generated in a single response (must be `>= 1`). Also the fallback for [`ModelPreset.max_output`](ModelPreset.md)
- `session_tokens_windows` (int): Default `65536` (64k). Fallback attention window used when the active preset does not declare `max_context` (must be `>= 1`)
- `llm_timeout` (int): Default `60`. API request timeout duration (seconds) (must be `>= 1`)
- `auto_retry` (bool): Default `True`. Automatically retry on request failure
- `max_retries` (int): Default `3`. Maximum number of retries (must be `>= 0`; `0` disables retrying)
- `max_fallbacks` (int): Default `5`. Maximum number of preset fallbacks (must be `>= 1`; `0` would make every request fail immediately)
- `enable_compaction` (bool): Default `True`. Whether to fold long history into a summary. The summary is stored on [`MemoryModel.abstract`](MemoryModel.md) and rendered into the system instruction by the train template
- `compaction_trigger_ratio` (float): Default `0.9`. Fraction of the attention window at which history compaction is forced (must be in `(0, 1]`). Kept below `1.0` to absorb the lag between the last measured prompt size and the next request's actual size
- `memory_length_limit` (int): Default `200`. Message-count fallback that forces compaction regardless of token accounting (must be `>= 0`; `0` disables the fallback)
- `enable_overflow_recovery` (bool): Default `True`. Whether to compact and retry once when the provider rejects a request for exceeding the context window
- `enable_multi_modal` (bool): Default `True`. Whether to enable multi-modal support (currently only supports image)

## Attention Window and Compaction

The attention window comes from the model, not from a global number. Each [`ModelPreset`](ModelPreset.md) can declare its own `max_context` (input budget) and `max_output` (response reservation); `session_tokens_windows` and `max_tokens` are only the fallbacks used when a preset leaves them unset. A model's real limit therefore follows the model.

Compaction fires on whichever trigger comes first:

- **Token trigger**: the prompt size the provider reported for the previous request reaches `compaction_trigger_ratio` × `max_context`. No local tokenizer is involved — the provider's own usage report is the measurement
- **Message-count fallback**: the history reaches `memory_length_limit` messages. This exists because the token trigger needs the provider to report usage; a gateway that reports none would otherwise let history grow without bound

A typical agent message (including tool calls and their results) costs roughly 300 tokens, so a 64k window is around 200 messages. Set `memory_length_limit` to `0` only if every provider you use reports usage.

## Description

The LLMConfig class inherits from BaseModel and is exposed as `AmritaConfig.llm`. It controls token limits, retry/fallback behavior, history compaction, and multi-modal support.

## Example

```python
from amrita_core.config import LLMConfig

llm_config = LLMConfig(
    enable_compaction=True,
    compaction_trigger_ratio=0.85,  # Fold once 85% of the window is in use
    memory_length_limit=200,  # Message-count fallback
    enable_overflow_recovery=True,  # Compact and retry on a provider overflow error
)
```
