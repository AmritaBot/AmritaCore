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
from amrita_core.tools.manager import MultiToolsManager
from amrita_core.tools.models import ToolData, ToolFunctionSchema

manager = MultiToolsManager()
manager.register_tool(
    ToolData(
        data=ToolFunctionSchema(function=STATUS_DEFINITION, strict=True),
        func=report_progress,
        custom_run=True,
    )
)
# 把 manager 作为会话的 ability.tools 传入（见数据层）
```

`MultiToolsManager` 持有多个命名管理器；会话解析分配给它的那一个。
`register_tool` 会拒绝重复的工具名，`disable_tool` / `enable_tool` 可以在不移除
注册的情况下隐藏某个工具。

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

**原理**：`custom_run` 是注册时的显式开关
（`on_tools(..., custom_run=True)`），保存在 `ToolData` 上。`call_tool()` 读这个
开关——它**不会**从 handler 签名推断模式，因此未开启该开关却写了 `ToolContext`
参数的工具，实际收到的会是参数 dict。

## 并发安全声明

同一条模型响应里的多个工具调用会被调度器分组执行。`concurrency_safe` 是注册时的
声明，保存在 `ToolData` 上，默认 `True`：

```python
@on_tools(WRITE_FILE_DEFINITION, concurrency_safe=False)
async def write_file(arguments: dict) -> str: ...
```

按参数判定时传一个可调用对象：

```python
@on_tools(QUERY_DEFINITION, concurrency_safe=lambda args: args.get("op") == "read")
async def query(arguments: dict) -> str: ...
```

`@simple_tool` 是装饰器形式，没法带上这项声明，因此用它注册的工具一律按无状态、
并发安全处理。需要声明不安全的工具，改用 `@on_tools(..., concurrency_safe=False)`
注册。

传 `False` 表示这个工具的调用必须独占执行，并成为同轮前后调用之间的屏障；传一个
可调用对象则按每次调用的参数判定，返回字面 `True` 才算安全。只有在你确定工具不会
改写父会话、共享文件或其他并发可见状态时才保留默认的 `True`——标错方向的代价是
竞态，而不是变慢。

## 让工具返回图片

`custom_run` 的 handler 也可以返回内容块，于是同一个调用里既能流出进度，又能交回
渲染结果：

```python
from amrita_core.types import Content, ImageContent, ImageUrl, TextContent


async def render_chart(tool_ctx: ToolContext) -> list[Content]:
    await tool_ctx.ctx.io_stream.yield_response("Rendering...")
    png = await chart(tool_ctx.data["query"])
    return [
        TextContent(text="chart ready"),
        ImageContent(image_url=ImageUrl(url=png)),
    ]
```

两种 handler 形态都接受 `TOOL_RESULT_CONTENT`（`str | list[Content]`）。
`list[Content]` 原样透传；其余返回值会被 JSON 编码成字符串，因此返回 `dict` 或
数字的 handler 行为不变。

`custom_run` 的 handler 返回 `None` 时，仍然得到
`"(this tool returned no content)"`。

两条值得记住的规则：

- **决定权在协议，不在你。** 图片究竟能不能抵达模型，取决于适配器的
  `features.tool_result_multimodal`。在声明为假的适配器上，网关会在发出去的副本里
  把块换成文本说明——你存下的历史仍保留原始块，后续回退到更强协议时什么都不会丢。
- **留一段文本。** 用一个 `TextContent` 说明这张图是什么。日志、`ERR:` 判错与历史
  压缩看的都是文本视图（`content_text()` / `ToolResult.text`）；一个只有图片的
  结果在那里会塌成 `<image>`，对这三者都没用。

### 纯文本适配器

Chat Completions 的 `tool` 消息装不下图片——这就是 `openai` 声明
`tool_result_multimodal=False` 的原因。如果你的部署只有 OpenAI 且这张图很重要，
别指望网关代劳：自己补一条 `user` 消息发过去，或者让工具返回一个 URL，下一轮再去
取。

## 校验约束

`FunctionPropertySchema` 支持完整 JSON Schema 约束集：

- 数值：`minimum`、`maximum`、`exclusiveMinimum`、`exclusiveMaximum`、`multipleOf`
- 字符串：`minLength`、`maxLength`、`pattern`、`format`
- 数组：`items`、`minItems`、`maxItems`、`uniqueItems`
- 对象：`properties`、`required`、`additionalProperties`
- 特殊：`enum`、`const`、`default`
- 联合：`type` 为列表（仅手动 schema）

参数会在 handler 运行前，由从 schema 编译出的校验器检查，因此非法调用永远到不了
你的函数——模型收到的是 `ERR:` 结果。投影/编译两轴的分工与
`validate_tool_arguments` 开关见
[工具系统（概念）](../concepts/tool.md#schema-与校验)。

## 工具调用模式

`config.builtin.tool_calling_mode` 控制可用性：

| 模式      | 行为                       |
| --------- | -------------------------- |
| `"agent"` | 完整工具调用（含内置工具） |
| `"rag"`   | 一轮检索，然后停止         |
| `"none"`  | 完全无工具                 |

## 下一步

[MCP 服务器](mcp-server.md)——把 MCP 工具暴露给 agent。
