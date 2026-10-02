# ReactConfig

ReAct agent reasoning-enhancement configuration.

## Description

`ReactConfig` progressively strengthens the built-in ReAct agent's reasoning through structured chain-of-thought decomposition, post-reasoning self-reflection, and reasoning-aware tool selection. It is exposed as `AmritaConfig.builtin.react_config`.

**Every option defaults to off** for backward compatibility: enabling nothing reproduces the plain ReAct loop.

## Properties

### Structured reasoning

- `structured_reasoning` (bool): Default `False`. Enable step-by-step structured reasoning with explicit phase markers (analyze / plan / execute / verify). When `True`, the reasoning template guides the model to decompose problems into numbered steps
- `reasoning_depth` (int): Default `3`, range `1..10`. Maximum reasoning chain depth (number of sub-problems). Used as a soft hint in the structured reasoning template

### Self-reflection

- `enable_reflection` (bool): Default `False`. After `STOP_TOOL`, call a `verify_reasoning` tool to check for contradictions, completeness, and alignment with the user's goal before generating the final answer
- `reflection_depth` (int): Default `1`, range `1..5`. Maximum number of reflection rounds. Each round may produce a correction that is fed back into the reasoning loop

### Reasoning-aware tool selection

- `reasoning_aware_tools` (bool): Default `False`. Tools predicted during structured reasoning are placed ahead of other tools in the tool list, nudging the model toward the most relevant tools first
- `tool_prediction` (bool): Default `False`. The structured reasoning template asks the model to list which tools it expects to need. **Requires `structured_reasoning=True` to be effective**

## Example

```python
from amrita_core.config import AmritaConfig, BuiltinAgentConfig, ReactConfig

config = AmritaConfig(
    builtin=BuiltinAgentConfig(
        react_config=ReactConfig(
            structured_reasoning=True,
            reasoning_depth=4,
            tool_prediction=True,
            reasoning_aware_tools=True,
            enable_reflection=True,
            reflection_depth=2,
        )
    )
)
```

## Related

- [BuiltinAgentConfig](BuiltinAgentConfig.md) — the parent object
- [ReActAgentStrategy](ReActAgentStrategy.md) — the strategy this configures
