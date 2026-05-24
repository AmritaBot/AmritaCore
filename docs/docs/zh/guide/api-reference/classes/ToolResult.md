# ToolResult

The ToolResult class represents the result of a tool invocation.

## Properties

- `role` (Literal["tool"]): Role, fixed as "tool"
- `name` (str): Tool name
- `content` (str): Tool return content
- `tool_call_id` (str): Tool call ID

## Description

The ToolResult class inherits from BaseModel and is used to represent the result of a tool invocation. When a tool completes execution, its result is encapsulated as a ToolResult object for use in the conversation flow.

ToolResult is an important component of AmritaCore's tool system, connecting tool invocation and subsequent conversation processing, allowing the AI model to understand and utilize the results of tool execution.
