# UniResponse

The UniResponse class provides a unified response format.

## Properties

- `role` (Literal["assistant"]): Role, fixed as "assistant"
- `usage` ([UniResponseUsage](UniResponseUsage.md) | None): Usage information, optional
- `content` (T): Response content, T is a generic parameter
- `tool_calls` (T_TOOL): Tool call results, T_TOOL is a generic parameter

## Description

The UniResponse class inherits from BaseModel and implements generics, providing a unified response format. It encapsulates the AI model's response content, usage statistics, and possible tool call results.

UniResponse is a core component of AmritaCore's response processing system, ensuring all responses from the AI model follow the same structure and format, facilitating subsequent processing and parsing.
