# BuiltinAgentConfig

Configuration for the built-in ReAct strategy.

## Properties

- `tool_calling_mode` (`Literal["agent", "rag", "none"]`): Default `"agent"`. Tool calling mode for Amrita's built-in agent strategy
- `agent_tool_call_notice` (`Literal["hide", "notify"]`): Default `"hide"`. How tool call status is shown in the built-in agent strategy — `"hide"` conceals it, `"notify"` reports it
- `agent_thought_mode` (`Literal["reasoning", "chat", "reasoning-required", "reasoning-optional"]`): Default `"chat"`. Thinking mode:
  - `"reasoning"` — perform the reasoning process first, then execute
  - `"reasoning-required"` — require task analysis for each tool call
  - `"reasoning-optional"` — do not require reasoning but allow it
  - `"chat"` — execute directly, no reasoning step
- `agent_reasoning_hide` (bool): Default `False`. Whether to hide the thought process
- `loop_reasoning_trigger` (int): Default `5`, minimum `1`. How many times a repeated tool signature is tolerated before the loop is broken
- `react_config` ([ReactConfig](ReactConfig.md)): Default `ReactConfig()`. ReAct reasoning enhancement configuration

## Description

`BuiltinAgentConfig` inherits from `BaseModel` and is exposed as `AmritaConfig.builtin`. It configures the behaviour of the built-in agent strategy — which tool-calling mode is used, how much of the reasoning process is surfaced, and when stall detection gives up.

## Example

```python
from amrita_core.config import AmritaConfig, BuiltinAgentConfig, ReactConfig

config = AmritaConfig(
    builtin=BuiltinAgentConfig(
        tool_calling_mode="agent",
        agent_thought_mode="reasoning",
        agent_tool_call_notice="notify",
        loop_reasoning_trigger=3,
        react_config=ReactConfig(structured_reasoning=True),
    )
)
```

## Related

- [ReactConfig](ReactConfig.md) — the nested reasoning-enhancement config
- [AmritaConfig](AmritaConfig.md) — the parent object
- [ReActAgentStrategy](ReActAgentStrategy.md) — the strategy this configures
