# Core Concepts

This section explains the fundamental ideas behind AmritaCore: what each component is, why it exists, and how the pieces fit together. If you are looking for step-by-step instructions, start with the [Tutorials](../tutorials/index.md) instead.

## Key Concepts

| Concept                                             | What it covers                                                                                                     |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [Configuration System](configuration.md)            | `AmritaConfig`, `FunctionConfig`, `LLMConfig`, `CookieConfig`, `BuiltinAgentConfig` — how AmritaCore is configured |
| [ChatObject — Conversation Objects](chat-object.md) | The core conversation class, presets, streaming, callbacks, and memory summarization                               |
| [Event System](event.md)                            | Hooks into the processing pipeline: pre-completion, completion, and fallback events                                |
| [Tool System](tool.md)                              | How tools are defined, registered, and invoked by the agent                                                        |
| [Agent Strategy](agent-strategy.md)                 | Strategy pattern for agent behavior: ReAct, Hybrid ReAct, NoAction                                                 |

## Data Management

The data layer separates **what data looks like** from **how data is stored**:

- [Data Management](data-management.md) — Overview of the data architecture
- [Data Containers](data-containers.md) — `Message`, `MemoryModel`, `StateContext`, tool registries, and MCP client managers
- [Data Backend](data-backend.md) — `AbilityBackend` / `MemoryBackend` interfaces and `LegacyBackend`
- [Data Misc](data-misc.md) — `ModelConfig`, `ModelPreset`, `UniResponse`, `SendMessageWrap`, and embedding chunks

## Where to Go Next

- Want to build your first agent? → [Tutorials](../tutorials/index.md)
- Need to implement a specific feature? → [How-to Guides](../how-to/function-implementation.md)
- Dive deeper into internals? → [Advanced](../advanced/index.md)
