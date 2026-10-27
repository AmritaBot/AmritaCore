# FunctionConfig

The FunctionConfig class defines functional behavior configuration for the Agent runtime.

## Properties

- `use_minimal_context` (bool): Default `False`. Whether to use minimal context, i.e. system prompt + user's last message. Disabling this option uses all context from the message list, which may consume a large amount of Tokens during Agent workflow execution; enabling it may effectively reduce token usage
- `agent_tool_call_limit` (int): Default `10`. Tool-calling round budget for one run (must be `>= 1`). A round is one model response that may request tools, so a round asking for three tools spends one unit, and a run may finish before the budget is spent. When the budget is spent the built-in strategies wind down instead of stopping mid-call, which lets the model still answer with what it has; a custom strategy that overrides `on_limited()` must call `super()` or set `_budget_exhausted` itself, otherwise the run breaks without a wind-down
- `agent_tool_parallel_limit` (int): Default `0`. How many concurrency-safe tool calls of one tool round may be in flight at once (must be `>= 0`). A round is one model response asking for tools, so this caps the calls inside a round, not the round budget of `agent_tool_call_limit`. `0` keeps the historical behaviour and lets every safe call of the round overlap; `1` forces serial execution. A settled call immediately makes room for the next one. Calls a tool declares unsafe, and the built-in flow-control tools, run alone regardless of this limit
- `agent_tool_refusal_rounds` (int): Default `2`. How many rounds the agent may keep asking for tools after `agent_tool_call_limit` is reached before the turn is closed (must be `>= 1`). Each such round answers every requested call with a refusal tool result instead of running it, so the model can still answer with what it has
- `validate_tool_arguments` (bool): Default `True`. Whether to check the arguments the model produced against each tool's parameter schema before the tool runs. A failed check is returned to the model as an `ERR:` tool result, which lets it correct the call; disable to pass arguments through untouched
- `agent_step_token_budget` (int): Default `-1`. Per-Step prompt-token budget for the built-in step loop (`<= 0` = disabled, i.e. unlimited). When the Step's accumulated prompt tokens reach this budget, the iteration loop stops
- `agent_middle_message` (bool): Default `True`. Whether to allow Agent to send intermediate messages to users during tool calling
- `agent_mcp_client_enable` (bool): Default `False`. Whether to enable MCP client
- `agent_mcp_server_scripts` (list[str]): Default `[]`. List of MCP server scripts

## Description

The FunctionConfig class inherits from BaseModel and is exposed as `AmritaConfig.function_config`. It controls runtime behavior of the agent: context usage, tool call limits, and MCP client integration.

## Example

```python
from amrita_core.config import FunctionConfig

func_config = FunctionConfig(
    agent_tool_call_limit=5,
    agent_tool_parallel_limit=4,
    agent_mcp_client_enable=True,
    agent_mcp_server_scripts=["path/to/mcp_server.py"],
)
```
