# ThinkingConfig

ThinkingConfig 类为支持的模型（如 OpenAI o1 系列、带扩展思考的 Anthropic Claude）配置思考/推理能力。

## 属性

- `thinking_type` (Literal["enabled", "disabled"] | None)：是否启用思考。会向 API 请求添加 `thinking.type` 属性（provider 相关）。默认：None
- `enable_thinking` (bool | None)：是否通过 `enable_thinking` 请求属性启用思考（provider 相关）。默认：None
- `thinking_effort` (str | None)：控制思考力度级别。取决于模型——典型值包括 `"minimal"`、`"low"`、`"medium"`、`"high"`、`"xhigh"` 或 `"max"`。默认：`"high"`
- `content_mode` (Literal["never", "by-tool", "optional"])：控制 `reasoning_content` 在消息历史中的处理方式：
  - `"never"`：剥离所有推理内容
  - `"by-tool"`：仅对包含 `tool_calls` 的 assistant 消息保留推理内容（Anthropic 的要求）
  - `"optional"`：原样透传推理内容（默认）

## 描述

ThinkingConfig 类继承自 BaseModel，提供对模型思考/推理行为的精细控制。它设置在
`ModelPreset.thinking_config` 上，由适配器（OpenAIAdapter、AnthropicAdapter）用于
配置思考相关的请求参数。

启用后，模型的推理过程通过以下方式暴露：

- `UniResponse.reasoning_content` — 思考/推理文本
- `UniResponse.reasoning_signature` — 用于往返传输的 Anthropic 签名
- `Message.reasoning_content` — 存储在对话历史中
- `Message.reasoning_signature` — 为 Anthropic API 往返传输而存储

## 示例

```python
from amrita_core.types import ThinkingConfig, ModelPreset

# 启用 Anthropic 扩展思考
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

# 启用 OpenAI o 系列推理
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
