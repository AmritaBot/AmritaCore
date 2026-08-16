# LLMConfig

LLMConfig 类定义 LLM 调用和记忆管理的配置参数。

## 属性

- `require_tools` (bool)：默认 `False`。是否强制每次调用至少使用一个工具
- `memory_length_limit` (int)：默认 `50`。记忆上下文中的最大消息数（必须 `>= 1`）
- `max_tokens` (int)：默认 `1000`。单次响应中生成的最大 token 数（必须 `>= 1`）
- `tokens_count_mode` (Literal["word", "bpe", "char"])：默认 `"bpe"`。token 计数模式
- `enable_tokens_limit` (bool)：默认 `True`。是否启用上下文长度限制
- `session_tokens_windows` (int)：默认 `5000`。会话 token 窗口大小（必须 `>= 1`）
- `llm_timeout` (int)：默认 `60`。API 请求超时时间（秒）（必须 `>= 1`）
- `auto_retry` (bool)：默认 `True`。请求失败时自动重试
- `max_retries` (int)：默认 `3`。最大重试次数（必须 `>= 0`；`0` 表示不重试）
- `max_fallbacks` (int)：默认 `5`。最大预设回退次数（必须 `>= 1`；`0` 会导致所有请求立即失败）
- `enable_memory_abstract` (bool)：默认 `True`。是否启用上下文记忆摘要
- `memory_abstract_proportion` (float)：默认 `0.5`。上下文摘要比例（必须在 `(0, 1]` 之间，如 `0.5` = 50%）
- `memory_abstract_threshold` (int)：默认 `-1`。触发 Step 边界历史压缩的 prompt-token 阈值（`<= 0` = 禁用，即永不）。当真实 API prompt-token 数在 Step 边界超过该值时，已完成的 Step 历史会被摘要进上下文
- `enable_multi_modal` (bool)：默认 `True`。是否启用多模态支持

## 示例

```python
from amrita_core.config import LLMConfig

llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15,
)
```
