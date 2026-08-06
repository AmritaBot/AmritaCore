# 自定义工具——进阶模式

## 本章目标

超越装饰器。学完你能：

- 用 `ToolsManager` 手动注册工具（会话级控制）
- 用 `custom_run` 模式在工具内触达框架
- 使用完整 JSON Schema 约束集

> **基础在哪里？** 工具概念、`@simple_tool` / `@on_tools` 装饰器与执行路径在
> [工具系统（概念）](../concepts/tool.md) 与[教程 2](../tutorials/tools.md)。
> 本页只覆盖它们没有的内容。

## 用 `ToolsManager` 手动注册

装饰器注册进全局容器。需要会话级控制时，自己注册进管理器实例：

```python
from amrita_core.tools.manager import ToolsManager

manager = ToolsManager()
manager.register(schema, handler, custom_run=False)
# 把 manager 作为会话的 ability.tools 传入（见数据层）
```

`MultiToolsManager` 持有多个命名管理器；会话解析分配给它的那一个。

## `custom_run`——需要框架访问的工具

需要框架（流式、会话状态）的工具使用 `custom_run`：handler 接收
`ToolContext` 而非裸 dict。

```python
from amrita_core import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
    ToolContext,
)

STATUS_DEFINITION = FunctionDefinitionSchema(
    name="report_progress",
    description="Report the agent's current progress to the user",
    parameters=FunctionParametersSchema(type="object", properties={}),
)


@on_tools(STATUS_DEFINITION)
async def report_progress(tool_ctx: ToolContext) -> str:
    # tool_ctx.data  —— 校验后的参数（dict）
    # tool_ctx.ctx   —— StrategyContext（config、io_stream……）
    stream = tool_ctx.ctx.io_stream
    await stream.yield_response("Working on it...")
    return "progress reported"
```

**原理**：`call_tool()` 检测 handler 签名——有 `ToolContext` 参数即切换为
`custom_run` 模式。

## 校验约束

`FunctionPropertySchema` 支持完整 JSON Schema 约束集：

- 数值：`minimum`、`maximum`、`exclusiveMinimum`、`exclusiveMaximum`、`multipleOf`
- 字符串：`minLength`、`maxLength`、`pattern`、`format`
- 数组：`items`、`minItems`、`maxItems`、`uniqueItems`
- 对象：`properties`、`required`、`additionalProperties`
- 特殊：`enum`、`const`、`default`
- 联合：`type` 为列表（仅手动 schema）

参数在 handler 运行前校验；非法调用永远到不了你的函数。

## 工具调用模式

`config.builtin.tool_calling_mode` 控制可用性：

| 模式      | 行为                       |
| --------- | -------------------------- |
| `"agent"` | 完整工具调用（含内置工具） |
| `"rag"`   | 一轮检索，然后停止         |
| `"none"`  | 完全无工具                 |

## 下一步

[MCP 服务器](mcp-server.md)——把 MCP 工具暴露给 agent。
