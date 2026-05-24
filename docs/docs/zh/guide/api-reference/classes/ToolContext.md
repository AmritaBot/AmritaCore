# ToolContext

ToolContext 类为 AmritaCore 中的自定义工具执行提供上下文。

## 描述

ToolContext 类是一个数据类，为使用 `custom_run=True` 注册的工具提供执行上下文。它包含传递给工具的参数和对当前策略执行上下文的访问。

## 属性

- `data` (dict[str, Any]): LLM 传递给工具的参数
- `ctx` ([StrategyContext](StrategyContext.md)): 当前策略执行上下文，包含：
  - `user_input`: 原始用户输入
  - `original_context`: 完整的消息上下文
  - `chat_object`: 对 [ChatObject](ChatObject.md) 的引用，用于生成响应

## 用法

ToolContext 会自动传递给使用 `custom_run=True` 参数注册的工具：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import ToolContext

@on_tools(data=my_tool_schema, custom_run=True)
async def my_custom_tool(ctx: ToolContext) -> str | None:
    # 访问工具参数
    param_value = ctx.data["param_name"]

    # 访问聊天对象以生成响应
    await ctx.ctx.chat_object.yield_response("处理中...")

    return f"结果: {param_value}"
```

此类确保在 AmritaCore 中所有自定义工具实现中一致地访问工具参数和执行上下文。
