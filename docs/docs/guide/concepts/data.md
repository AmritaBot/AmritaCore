# Data Management

How data flows through AmritaCore: messages, memory, backends, and the DI
contexts that carry state between workflow nodes.

## Messages

| Type              | Role                                                                        |
| ----------------- | --------------------------------------------------------------------------- |
| `Message`         | One conversation message (role, content, `tool_calls`, `reasoning_content`) |
| `ToolResult`      | A tool's output, paired with its `tool_call_id`                             |
| `SendMessageWrap` | The working context: `train` + `memory` + `user_query` + `end_messages`     |
| `UniResponse`     | Normalized LLM response (content, tool_calls, `reasoning_content`, usage)   |

`SendMessageWrap` is what strategies mutate — `ctx.message.append(...)` adds to
`end_messages`, which `unwrap()` includes in the next request.

## DI Contexts

Workflow nodes receive state via **type-matched injection** — each node
declares parameters like `loop: AgentLoopState` and the interpreter injects
the matching instance. Key contexts (all owned by `ChatObject`):

| Context              | Carries                           |
| -------------------- | --------------------------------- |
| `SessionMetadata`    | session/stream ids, timestamps    |
| `MemoryContext`      | runtime memory                    |
| `AbilityState`       | config, preset, backend slots     |
| `GeneralInput`       | user input, train, template       |
| `WorkingState`       | the `SendMessageWrap`             |
| `RespState`          | response + usage                  |
| `AgentLoopState`     | strategy, call count, `run_state` |
| `StrategyPayload`    | the strategy factory              |
| `DatabackendOptions` | backend fetch/commit skip flags   |

> In AmritaSense terms this is the standard dependency-injection mechanism —
> see [sense.amritabot.com](https://sense.amritabot.com) for the general rules.

## Two Deep-Dives

| Page                            | Covers                                                                           |
| ------------------------------- | -------------------------------------------------------------------------------- |
| [Data Backend](data-backend.md) | The `AbilityBackend` / `MemoryBackend` interfaces and how to write your own      |
| [Memory Model](data-memory.md)  | `MemoryModel`, the load/commit lifecycle, and the legacy `StateContext` accessor |

## Next

[Extensions & Integration](../extensions-integration/index.md) — adapters,
tools, MCP and tokenizers.
