# LLMConfig

The LLMConfig class defines configuration parameters for LLM calls and memory management.

## Properties

- `require_tools` (bool): Default `False`. Whether to force at least one tool to be used per call
- `memory_length_limit` (int): Default `50`. Maximum number of messages in memory context
- `max_tokens` (int): Default `1000`. Maximum number of tokens generated in a single response
- `tokens_count_mode` (Literal["word", "bpe", "char"]): Default `"bpe"`. Token counting mode: bpe (subwords) / word (words) / char (characters)
- `enable_tokens_limit` (bool): Default `True`. Whether to enable context length limits
- `session_tokens_windows` (int): Default `5000`. Session tokens window size
- `llm_timeout` (int): Default `60`. API request timeout duration (seconds)
- `auto_retry` (bool): Default `True`. Automatically retry on request failure
- `max_retries` (int): Default `3`. Maximum number of retries
- `max_fallbacks` (int): Default `5`. Maximum number of preset fallbacks
- `enable_memory_abstract` (bool): Default `True`. Whether to enable context memory summarization (deletes context and inserts a summary into system instruction)
- `memory_abstract_proportion` (float): Default `0.5`. Context summarization proportion (0.5 = 50%)
- `memory_abstract_threshold` (int | None): Default `None`. Prompt-token threshold that triggers between-Step history compression (`None` = never). When the real API prompt-token count exceeds this value at a Step boundary, completed-Step history is summarized into the context
- `enable_multi_modal` (bool): Default `True`. Whether to enable multi-modal support (currently only supports image)

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
