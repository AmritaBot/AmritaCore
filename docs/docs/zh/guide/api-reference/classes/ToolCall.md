# ToolCall

The ToolCall class represents an invocation of a tool.

## Properties

- `id` (str): ID of the tool call
- `function` ([Function](Function.md)): Function called by the model
- `type` (typing.Literal["function"]): Tool type, currently only supports "function"

## Description

The ToolCall class inherits from BaseModel and is used to represent tool invocations initiated by the AI model. When the AI model determines that a particular tool needs to be invoked, it generates a ToolCall object containing information about the function to call and its arguments.

ToolCall is a key component of AmritaCore's tool calling system, allowing the AI model to interact with external tools and services.
