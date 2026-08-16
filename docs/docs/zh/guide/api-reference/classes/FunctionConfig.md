# FunctionConfig

FunctionConfig 类定义 Agent 运行时的功能行为配置。

## 属性

- `use_minimal_context` (bool)：默认 `False`。是否使用最简上下文（即系统提示 + 用户最后一条消息）。禁用此选项会在 Agent 工作流执行期间使用消息列表中的所有上下文，可能消耗大量 Token；启用可有效减少 token 用量
- `no_tokenizer` (bool)：默认 `False`。当响应不返回 token 计数时禁用内置分词器
- `tokenizer_used` (str)：默认 `"simple"`。要使用的分词器
- `agent_tool_call_limit` (int)：默认 `10`。调用工具时的工具调用限制（必须 `>= 1`）
- `agent_step_token_budget` (int)：默认 `-1`。内置 step 循环的每 Step prompt-token 预算（`<= 0` = 禁用，即不限）。当该 Step 累计 prompt token 达到预算时，迭代循环停止
- `agent_middle_message` (bool)：默认 `True`。是否允许 Agent 在工具调用期间向用户发送中间消息
- `agent_mcp_client_enable` (bool)：默认 `False`。是否启用 MCP 客户端
- `agent_mcp_server_scripts` (list[str])：默认 `[]`。MCP 服务器脚本列表

## 描述

FunctionConfig 类继承自 BaseModel，通过 `AmritaConfig.function_config` 公开。它控制 agent 的运行时行为：上下文使用、分词器选择、工具调用限制和 MCP 客户端集成。

## 示例

```python
from amrita_core.config import FunctionConfig

func_config = FunctionConfig(
    tokenizer_used="my_tokenizer",
    agent_tool_call_limit=5,
    agent_mcp_client_enable=True,
    agent_mcp_server_scripts=["path/to/mcp_server.py"],
)
```
