# UniResponse

UniResponse 类提供统一的响应格式。

## 属性

- `role` (Literal["assistant"])：角色，固定为 "assistant"
- `usage` ([UniResponseUsage](UniResponseUsage.md) | None)：使用信息，可选
- `content` (T)：响应内容，T 是泛型参数
- `tool_calls` (T_TOOL)：工具调用结果，T_TOOL 是泛型参数
- `reasoning_content` (str | None)：模型的推理/思考内容
- `reasoning_signature` (str | None)：Anthropic 思考签名
- `metadata` ([RequestMetadata](RequestMetadata.md))：请求元数据

## 描述

UniResponse 类继承自 BaseModel 并实现泛型，提供统一的响应格式。它封装了 AI 模型的响应内容、使用统计和可能的工具调用结果。
