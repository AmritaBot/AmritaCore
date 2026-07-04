# UniResponse

The UniResponse class provides a unified response format.

## Properties

- `role` (Literal["assistant"]): Role, fixed as "assistant"
- `usage` ([UniResponseUsage](UniResponseUsage.md) | None): Usage information, optional
- `content` (T): Response content, T is a generic parameter
- `tool_calls` (T_TOOL): Tool call results, T_TOOL is a generic parameter
- `reasoning_content` (str | None): Reasoning/thinking content from the model, if the model supports it (e.g., o1, Claude with extended thinking)
- `reasoning_signature` (str | None): Anthropic thinking signature, required for round-tripping thinking content with Anthropic API
- `metadata` ([RequestMetadata](RequestMetadata.md)): 请求元数据，包含请求 ID、模型名称、停止原因和原始提供商请求 ID

## Description

The UniResponse class inherits from BaseModel and implements generics, providing a unified response format. It encapsulates the AI model's response content, usage statistics, and possible tool call results.

UniResponse is a core component of AmritaCore's response processing system, ensuring all responses from the AI model follow the same structure and format, facilitating subsequent processing and parsing.
