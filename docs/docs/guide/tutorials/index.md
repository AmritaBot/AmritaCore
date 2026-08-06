# Tutorials

This section walks you through building agents with AmritaCore **step by step**.
Each tutorial builds on the previous one and uses the public API only — no
internals required.

## Prerequisites

- Python 3.10+ with `amrita-core` installed (see [Getting Started](../getting-started/index.md))
- An LLM API endpoint (OpenAI-compatible or Anthropic)
- Basic familiarity with `async`/`await`

## Tutorial Path

| #   | Tutorial                                  | What you will build                                         |
| --- | ----------------------------------------- | ----------------------------------------------------------- |
| 1   | [Create Your First Agent](chat-object.md) | A minimal chat agent with `create_agent()` and `ChatObject` |
| 2   | [Add Tools to Your Agent](tools.md)       | Register callable tools with `@simple_tool` and `@on_tools` |
| 3   | [Streaming and Callbacks](streaming.md)   | Stream responses, read metadata, use callbacks              |
| 4   | [Events and Hooks](event-hooks.md)        | Intercept the pipeline with lifecycle events                |
| 5   | [Memory and Sessions](memory.md)          | Persist conversation history with `session_id`              |

Each tutorial takes about 5–10 minutes. Already comfortable? Jump to
[Concepts](../concepts/index.md) to understand the internals, or
[Extensions & Integration](../extensions-integration/index.md) to plug in your
own tools, adapters and MCP servers.
