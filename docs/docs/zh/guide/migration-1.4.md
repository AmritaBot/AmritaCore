# 迁移指南：1.3 → 1.4

AmritaCore 1.4 允许工具返回文本之外的东西——图片、文件引用——并把适配器的能力标记
收进一个 `FeatureFlag`。已有的工具与适配器继续可用；文末清单列出了需要复查的点。

## 一览

| 变更                                        | 需要做什么                                                                                                                  |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `ToolResult.content`                        | 类型从 `str` 放宽为 `str \| list[Content]`。把 `.content` 当字符串读的代码请改用 `.text`（或 `content_text()`）。           |
| 工具 handler                                | 可以返回 `str \| list[Content]`。其余返回值仍会被 JSON 编码，因此无需改动。                                                 |
| `ModelAdapter.supports_agentic_call`        | 已弃用。请读 `features.agentic_call`；旧字段会在类创建时被翻译并保持同步，第三方适配器不改也能继续工作。                    |
| `ModelAdapter.features`（新增 `FeatureFlag`） | 适配器现在声明自己能往 wire 上放什么。协议携带不了的由网关降级。                                                            |
| `StepToolReturnEvent.result`                | 类型同步放宽；把它当字符串读的 matcher 请改用 `content_text()`。                                                            |

## 1. 工具结果可以是内容块

`ToolResult.content` 现在是 `TOOL_RESULT_CONTENT`（`str | list[Content]`）。返回
`list[Content]`——文本、图片、文件块——的工具，其结果会被原样保存与转发：

```python
@simple_tool
async def screenshot(url: str) -> list[Content]:
    """Capture a page."""
    return [
        TextContent(text=f"captured {url}"),
        ImageContent(image_url=ImageUrl(url=png)),
    ]
```

`list[Content]` 原样透传；**其余任何**返回值仍会被 JSON 编码成字符串，与从前一致。
返回 `dict`、数字或由 dict 组成的普通 `list`，行为都不变。

wire 之外的一切读的都是文本视图：

```python
result.text  # "captured https://...<image>"
content_text(result.content)
```

非文本块在那里塌成 `<image>` / `<file:name>`。如果你的代码里有
`result.content.startswith(...)`，或者把 `.content` 传进了字符串 API，请改成
`.text`。`StepToolReturnEvent.result` 同理——检查结果的 matcher 应走
`content_text()`。

## 2. 能力统一在 `FeatureFlag` 里声明

`supports_agentic_call` 过去用一个布尔量描述一种能力。现在有三种，而且描述的是
**wire**，不是模型：

```python
from amrita_core.base.adapter import FeatureFlag, ModelAdapter


class MyAdapter(ModelAdapter):
    features = FeatureFlag(
        agentic_call=True,  # 实现了 agentic_call_api()
        input_multimodal=True,  # user/system 内容里的非文本块
        tool_result_multimodal=False,  # tool 消息内容里的非文本块
    )
```

默认全为 `False`——标记是一种声明，什么都没说的适配器按「什么都带不了」处理。

兼容性：只声明了 `supports_agentic_call = True` 的适配器，会在类创建时被翻译成
`features.agentic_call`，且旧属性与新标记保持同步。不会坏；该字段是弃用，不是移除。

子类请**整个** `FeatureFlag` 赋值——它是 frozen dataclass，本来就不支持就地改字段。

## 3. 协议带不了的，网关负责降级

每次请求前，网关查看目标适配器的 `features`，把协议携带不了的块在消息的**副本**上
换成文本说明：

```
<image omitted: the current adapter cannot carry it>
```

几个值得知道的后果：

- **存储侧历史不动。** 后续回退到更强的适配器时，原始块还在。
- **每个 (协议, 载荷种类) 只告警一次。** 长跑进程不会刷屏，也不会在第一轮之后再提醒。
- **回退会重新协商。** 每次尝试都按真正要用的那个 preset 整理载荷，因此运行中途换
  协议也能处理。
- **`file` 块目前任何内置适配器都带不了。** Anthropic 端点需要
  `source.type="file"` 加 `anthropic-beta: files-api-2025-04-14` 头，适配器还没有
  注入请求头的通道；该块会变成 `<file:name omitted: ...>` 而不是凭空消失。此前它是
  被静默丢弃的，结果是模型对着一份从未收到的文件作答。

内置适配器的声明：

| 适配器                      | `input_multimodal` | `tool_result_multimodal` |
| --------------------------- | ------------------ | ------------------------ |
| `openai`（Chat Completions） | ✅                 | ❌                       |
| `anthropic`（Messages）      | ✅                 | ✅                       |

## 检查清单

- [ ] 把 `ToolResult.content` 当字符串读的代码，改用 `.text`。
- [ ] 读 `StepToolReturnEvent.result` 的 matcher，改用 `content_text()`。
- [ ] 自定义适配器声明 `features`（或保留已弃用的 `supports_agentic_call`，仍然有效）。
- [ ] 如果依赖工具返回的图片，确认你的适配器声明了 `tool_result_multimodal`，
      否则网关会把它们换成文本说明。
