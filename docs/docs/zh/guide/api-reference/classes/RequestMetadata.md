# RequestMetadata

`RequestMetadata` 捕获每次请求的诊断信息，通过 `UniResponse.metadata` 返回。

## 属性

- `request_id` (str): 自动生成的唯一请求 ID（UUID4）。未提供时默认为新的 UUID。
- `original_request_id` (str | None): LLM 提供商适配器返回的原始请求 ID（如 OpenAI 的 `_request_id`、Anthropic 的 `request_id`）。不可用时为 `None`。
- `model` (str): 请求使用的模型。不可用时默认为 `"__NOT_GIVEN__"`（如流式传输中首个 chunk 到达前）。
- `stop_sequence` (str | None): 导致生成终止的停止序列。
- `stop_reason` (STOP_REASON | None): 生成停止的原因。可选值：

  | 值                | 含义                |
  | ----------------- | ------------------- |
  | `"end_turn"`      | 自然完成            |
  | `"max_tokens"`    | 达到最大 token 限制 |
  | `"stop_sequence"` | 匹配到停止序列      |
  | `"tool_use"`      | 模型调用了工具      |
  | `"pause_turn"`    | Anthropic 暂停回合  |
  | `"refusal"`       | 内容被过滤/拒绝     |

## 用法

```python
from amrita_core.types.response import RequestMetadata

# 通过 UniResponse 访问
response: UniResponse = ...
print(response.metadata.model)          # 例如 "gpt-4o"
print(response.metadata.stop_reason)    # 例如 "end_turn"
print(response.metadata.original_request_id)  # 提供商的请求 ID
```

> **注意**：配置了 `extra="allow"`，因此除标准字段外可能还会出现提供商特定的字段。
