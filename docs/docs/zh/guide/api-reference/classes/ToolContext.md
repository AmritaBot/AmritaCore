# ToolContext

ToolContext 类为 AmritaCore 中的自定义工具执行提供上下文。

## 属性

- `data` (dict[str, Any])：LLM 传递给工具的参数
- `ctx` ([StrategyContext](StrategyContext.md))：当前策略执行上下文

## 使用

ToolContext 自动传递给使用 `custom_run=True` 参数注册的工具：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import ToolContext

@on_tools(data=my_tool_schema, custom_run=True)
async def my_custom_tool(ctx: ToolContext) -> str | None:
    param_value = ctx.data["param_name"]
    await ctx.ctx.chat_object.yield_response("处理中...")
    return f"结果：{param_value}"
```
