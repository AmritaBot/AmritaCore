# FunctionConfig

The FunctionConfig class defines functional behavior configuration for the Agent runtime.

## Properties

- `use_minimal_context` (bool): Default `False`. Whether to use minimal context, i.e. system prompt + user's last message. Disabling this option uses all context from the message list, which may consume a large amount of Tokens during Agent workflow execution; enabling it may effectively reduce token usage
- `no_tokenizer` (bool): Default `False`. Disable built-in tokenizer when response is not returning a token count
- `tokenizer_used` (str): Default `"simple"`. Tokenizer to use
- `agent_tool_call_limit` (int): Default `10`. Tool call limit when calling tools
- `agent_middle_message` (bool): Default `True`. Whether to allow Agent to send intermediate messages to users during tool calling
- `agent_mcp_client_enable` (bool): Default `False`. Whether to enable MCP client
- `agent_mcp_server_scripts` (list[str]): Default `[]`. List of MCP server scripts

## Description

The FunctionConfig class inherits from BaseModel and is exposed as `AmritaConfig.function_config`. It controls runtime behavior of the agent: context usage, tokenizer selection, tool call limits, and MCP client integration.

## Example

```python
from amrita_core.config import FunctionConfig

func_config = FunctionConfig(
    tokenizer_used="my_tokenizer",
    agent_tool_call_limit=5,
    agent_mcp_client_enable=True,
    agent_mcp_server_scripts=["path/to/mcp_server.py"],
)
```
