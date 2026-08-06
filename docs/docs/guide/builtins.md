# Built-in Capabilities

## Built-in Tools

| Tool                               | Purpose                                                                                |
| ---------------------------------- | -------------------------------------------------------------------------------------- |
| `STOP_TOOL` (`agent_stop`)         | Ends the tool loop; the agent answers directly                                         |
| `REASONING_TOOL` (`reasoning`)     | Explicit reasoning step (non-native-thinking mode)                                     |
| `UPDATE_STEP_TOOL` (`update_step`) | Revise the task plan: `replan` / `mark_done` / `add_step` / `remove_step`              |
| `PROCESS_MESSAGE`                  | Reports agent progress to the user (enabled by `function_config.agent_middle_message`) |

Built-in tools bypass the `agent.tool_call` / `agent.tool_return` lifecycle
events and are excluded from stall-signature cancellation.

## Built-in Metadata Types

Stream metadata (`MessageWithMetadata.metadata`) uses `type` + `extra_type`:

| `type`                               | `extra_type`                                           | Meaning                                                      |
| ------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------------ |
| `function_call`                      | —                                                      | Tool start/finish (`is_done`)                                |
| `reasoning_chunk`                    | `cot_chunk`                                            | Thinking-mode reasoning streaming                            |
| `reasoning` / `structured_reasoning` | —                                                      | Reasoning summaries                                          |
| `reflection`                         | —                                                      | Post-stop reflection results                                 |
| `error`                              | `loop_reasoning`                                       | Loop-detection error notice                                  |
| `step`                               | `decompose` / `intro` / `leave` / `stall` / `compress` | Step-loop lifecycle (see [Step Loop](advanced/step-loop.md)) |

## Built-in Adapters

See [Model Adapters](extensions-integration/adapters.md) — OpenAI-compatible
(OpenAI/DeepSeek/Azure) and Anthropic.

## Built-in Strategies

| Strategy                   | Category      | Notes                                                                            |
| -------------------------- | ------------- | -------------------------------------------------------------------------------- |
| `ReActAgentStrategy`       | `agent-mixed` | **Default**; step-driven loop (see [Agent Strategy](concepts/agent-strategy.md)) |
| `HybridReActAgentStrategy` | `agent-mixed` | MoE XML-style results; **deprecated, removed in v0.14.0**                        |
| `NoActionAgentStrategy`    | `workflow`    | Skip tool calling                                                                |

## Built-in Event Hooks

### Cookie Security Hook

When `config.cookie.enable_cookie = True`, responses are scanned for
configured cookie values; on a match the session terminates with a generic
error to prevent data leakage (see [Security](security-mechanisms.md)).

### Post-Process Hook

`strategy.on_post_process()` runs after successful execution for all strategy
categories — final instructions, summarization, or cleanup.

## Built-in Workflows

Pre-composed pipelines in `amrita_core.builtins.workflows`
(see [Workflow Engine](advanced/workflow-engine.md)):

| Workflow                                                     | Pipeline                           |
| ------------------------------------------------------------ | ---------------------------------- |
| `STEP_REACT_BLOCK` / `SIMPLE_STEP_REACT` / `STEP_REACT_ONLY` | Step-driven ReAct (default family) |
| `REACT_BLOCK` / `SIMPLE_REACT` / `REACT_ONLY`                | Legacy ReAct loop                  |
| `SIMPLE_CHAT`                                                | Plain chat, no agent               |
