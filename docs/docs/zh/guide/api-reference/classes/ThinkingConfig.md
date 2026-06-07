# ThinkingConfig

ThinkingConfig 类为支持的模型（如 OpenAI o1 系列、Anthropic Claude 扩展思考）配置思考/推理能力。

## 属性

- `thinking_type` (Literal["enabled", "disabled"] | None): 是否启用思考。向 API 请求中添加 `thinking.type` 属性（因提供商而异）。默认：None
- `enable_thinking` (bool | None): 是否通过 `enable_thinking` 请求属性启用思考（因提供商而异）。默认：None
- `thinking_effort` (str | None): 控制思考努力级别。因模型而异 — 典型值包括 `"minimal"`、`"low"`、`"medium"`、`"high"`、`"xhigh"` 或 `"max"`。默认：`"high"`
- `content_mode` (Literal["never", "by-tool", "optional"]): 控制消息历史中 `reasoning_content` 的处理方式：
  - `"never"`: 移除所有推理内容
  - `"by-tool"`: 仅保留包含 `tool_calls` 的助手消息的推理内容（Anthropic 要求）
  - `"optional"`: 原样透传推理内容（默认）

## 描述

ThinkingConfig 类继承自 BaseModel，提供对模型思考/推理行为的细粒度控制。它设置在 `ModelPreset.thinking_config` 上，由适配器（OpenAIAdapter、AnthropicAdapter）用于配置与思考相关的请求参数。

启用后，模型的推理过程通过以下方式暴露：

- `UniResponse.reasoning_content` — 思考/推理文本
- `UniResponse.reasoning_signature` — Anthropic 签名（用于往返传输）
- `Message.reasoning_content` — 存储在对话历史中
- `Message.reasoning_signature` — 存储用于 Anthropic API 往返传输

## 示例

```python
from amrita_core.types import ThinkingConfig, ModelPreset

# 为 Anthropic 启用扩展思考
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

# 为 OpenAI o 系列启用推理
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
