# ToolContext

ToolContext 类为 AmritaCore 中的自定义工具执行提供上下文。

## 描述

ToolContext 类是一个 dataclass，为以 `custom_run=True` 注册的工具提供执行上下文
。它既包含传给工具的参数，也提供对当前策略执行上下文的访问。

## 属性

- `data` (dict[str, Any])：LLM 传递给工具的参数
- `ctx` ([StrategyContext](StrategyContext.md))：当前策略执行上下文，包含：
  - `user_input`：原始用户输入
  - `original_context`：完整的消息上下文
  - `chat_object`：用于产出响应的 [ChatObject](ChatObject.md) 引用

## 使用

ToolContext 会自动传给以 `custom_run=True` 参数注册的工具：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import ToolContext


@on_tools(data=my_tool_schema, custom_run=True)
async def my_custom_tool(ctx: ToolContext) -> str | None:
    # 访问工具参数
    param_value = ctx.data["param_name"]

    # 访问 chat object 以产出响应
    await ctx.ctx.chat_object.yield_response("处理中...")

    return f"结果：{param_value}"
```

该类确保 AmritaCore 中所有自定义工具实现都能以一致的方式同时访问工具参数与执行
上下文。
