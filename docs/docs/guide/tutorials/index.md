# Tutorials

This section walks you through building agents with AmritaCore step by step. Each tutorial builds on the previous one, and all of them use the recommended [`create_agent()`](../api-reference/index.md#create_agent) factory function — the simplest way to get started.

> **Note**: The examples in these tutorials use the public API only. For an in-depth explanation of the concepts behind each step, see the [Core Concepts](../concepts/index.md) section.

## Prerequisites

- Python 3.10+ with `amrita_core` installed
- An LLM API endpoint (OpenAI-compatible, Anthropic, or any [supported adapter](../api-reference/index.md#backends--contexts))
- Basic familiarity with `async`/`await` in Python

## Tutorial Path

| Tutorial                                     | What you will build                                                |
| -------------------------------------------- | ------------------------------------------------------------------ |
| [1. Create Your First Agent](chat-object.md) | A minimal chat agent using `create_agent()`                        |
| [2. Add Tools to Your Agent](tools.md)       | Register callable tools with `@simple_tool` and `@on_tools`        |
| [3. Streaming and Callbacks](streaming.md)   | Stream responses token by token and hook in callbacks              |
| [4. Events and Hooks](event-hooks.md)        | Intercept the pipeline with `@on_completion` / `@on_precompletion` |
| [5. Memory and Sessions](memory.md)          | Persist conversation history across turns with `session_id`        |

Each tutorial takes about 5–10 minutes. If you prefer reading a single self-contained example first, the [Minimal Example](../getting-started/minimal-example.md) in Getting Started is a good starting point.

## Where to Go Next

- Understand the internals → [Core Concepts](../concepts/index.md)
- Implement a specific feature → [How-to Guides](../how-to/function-implementation.md)
- Explore suspend/resume and workflows → [Advanced](../advanced/index.md)
