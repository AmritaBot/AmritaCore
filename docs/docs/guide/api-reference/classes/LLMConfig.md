# LLMConfig

The LLMConfig class defines configuration parameters for LLM calls and memory management.

## Properties

- `require_tools` (bool): Default `False`. Whether to force at least one tool to be used per call
- `memory_length_limit` (int): Default `200`. Maximum number of messages in memory context (must be `>= 1`)
- `max_tokens` (int): Default `1000`. Maximum number of tokens generated in a single response (must be `>= 1`)
- `tokens_count_mode` (Literal["word", "bpe", "char"]): Default `"bpe"`. Token counting mode: bpe (subwords) / word (words) / char (characters)
- `enable_tokens_limit` (bool): Default `True`. Whether to enable context length limits
- `session_tokens_windows` (int): Default `65536` (64k). Session tokens window size (must be `>= 1`)
- `llm_timeout` (int): Default `60`. API request timeout duration (seconds) (must be `>= 1`)
- `auto_retry` (bool): Default `True`. Automatically retry on request failure
- `max_retries` (int): Default `3`. Maximum number of retries (must be `>= 0`; `0` disables retrying)
- `max_fallbacks` (int): Default `5`. Maximum number of preset fallbacks (must be `>= 1`; `0` would make every request fail immediately)
- `enable_memory_abstract` (bool): Default `True`. Whether to enable context memory summarization (deletes context and inserts a summary into system instruction)
- `memory_abstract_proportion` (float): Default `0.5`. Context summarization proportion (must be in `(0, 1]`; e.g. `0.5` = 50%)
- `memory_abstract_threshold` (int): Default `-1`. Prompt-token threshold that triggers between-Step history compression (`<= 0` = disabled, i.e. never). When the real API prompt-token count exceeds this value at a Step boundary, completed-Step history is summarized into the context
- `enable_multi_modal` (bool): Default `True`. Whether to enable multi-modal support (currently only supports image)

## Window Size vs. Message Count

`session_tokens_windows` and `memory_length_limit` are two independent compression triggers: context is compacted as soon as either one is reached.

Raising only the token window without relaxing the message cap is therefore not enough. The message-count limit will fire first, context gets trimmed far more often than necessary, and prompt cache hit rate drops.

Rule of thumb: in a typical agent task, one message (including tool calls and their results) costs roughly 300 tokens. So:

- 64k context ~ 200 messages (the defaults follow this ratio)
- 128k context ~ 400 messages
- 256k context ~ 800 messages

Scale both values together to match the model's actual context window.

## Description

The LLMConfig class inherits from BaseModel and is exposed as `AmritaConfig.llm`. It controls token limits, retry/fallback behavior, memory summarization, and multi-modal support.

## Example

```python
from amrita_core.config import LLMConfig

llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15,  # Summarize a portion of the conversation when reaching the token limit
)
```
