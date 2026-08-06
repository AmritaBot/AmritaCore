# RequestMetadata

`RequestMetadata` 捕获每次适配器调用返回的请求诊断信息，通过 `UniResponse.metadata` 访问。

## 属性

- `request_id` (str)：自动生成的唯一请求 ID（UUID4）
- `original_request_id` (str | None)：LLM 提供商适配器返回的原始请求 ID
- `model` (str)：请求使用的模型。默认 `"__NOT_GIVEN__"`
- `stop_sequence` (str | None)：终止生成的停止序列
- `stop_reason` (STOP_REASON | None)：生成停止的原因：

  | 值                | 含义                |
  | ----------------- | ------------------- |
  | `"end_turn"`      | 自然完成            |
  | `"max_tokens"`    | 达到最大 token 限制 |
  | `"stop_sequence"` | 匹配停止序列        |
  | `"tool_use"`      | 模型调用了工具      |
  | `"pause_turn"`    | Anthropic 暂停回合  |
  | `"refusal"`       | 内容被过滤/拒绝     |

## 使用

```python
from amrita_core.types.response import RequestMetadata

# 通过 UniResponse 访问
response: UniResponse = ...
print(response.metadata.model)  # 例如 "gpt-4o"
print(response.metadata.stop_reason)  # 例如 "end_turn"
```
