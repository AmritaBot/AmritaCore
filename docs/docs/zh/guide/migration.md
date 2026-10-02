# 迁移指南：0.13 → 1.0

AmritaCore 1.0 移除了本地分词器，并把上下文管理改为以模型自身的注意力窗口为准。
本页列出全部破坏性变更及其替代方案。

## 一览表

| 移除 / 改名                                                       | 替代                                                            |
| ----------------------------------------------------------------- | --------------------------------------------------------------- |
| `amrita_core.tokenizer` 模块                                      | provider 上报的 usage（`MemoryModel.usage`）                    |
| `TokenizerManager`、`BaseTokenizer`                               | （无——分词是 provider 的职责）                                  |
| `get_tokens()`、`hybrid_token_count()`                            | provider 响应中的 `UniResponseUsage`                            |
| `FunctionConfig.no_tokenizer`                                     | （无）                                                          |
| `FunctionConfig.tokenizer_used`                                   | （无）                                                          |
| `LLMConfig.tokens_count_mode`                                     | （无）                                                          |
| `LLMConfig.enable_tokens_limit`                                   | （无）                                                          |
| 请求中的 `config.llm.max_tokens`                                  | `resolve_max_output(preset, config)`                            |
| `LLMConfig.enable_memory_abstract`                                | `LLMConfig.enable_compaction`                                   |
| `LLMConfig.memory_abstract_proportion`                            | `LLMConfig.compaction_trigger_ratio`                            |
| `LLMConfig.memory_abstract_threshold`                             | `LLMConfig.compaction_trigger_ratio`（+ `memory_length_limit`） |
| `chatmanager.MemoryLimiter`                                       | `ContextCompactor` + `NORMALIZE_MESSAGES`                       |
| `UsageRegistry` 系列                                              | `SessionUsageProxy`                                             |
| `ChatObject(context=...)`                                         | `ChatObject(session_id=...)`（现在必填）                        |
| `chat.state` / `StateContext`                                     | `chat.session_id`、`chat.data`、DI 上下文                       |
| `LegacyBackend(ctx=...)`                                          | `LegacyBackend()`                                               |
| `HybridReActAgentStrategy`                                        | `ReActAgentStrategy`                                            |
| `BuiltinName`                                                     | （无）                                                          |
| 工具参数不做校验                                                  | `function_config.validate_tool_arguments`（默认 `True`）        |
| `SuspendEnum.MEMORY_APPEND`、`.FINALIZE`、`.CALL_SINGLE_STRATEGY` | （无——从未发出过）                                              |
| `BuiltinAgentConfig.agent_tool_call_notice`                       | （无——请过滤流）                                                |
| `BuiltinAgentConfig.agent_reasoning_hide`                         | （无——请过滤流）                                                |

## 1. 分词器已移除

AmritaCore 不再附带分词器，`jieba` 也不再是可选依赖。token 统计改为使用
provider 随每次响应一并返回的数字：

```python
# 之前
from amrita_core import get_tokens

tokens = get_tokens(messages)

# 之后
tokens = chat.data.usage  # UniResponseUsage | None，来自上一次请求
```

provider 应答的每次补全都会把 usage 写回 `MemoryModel.usage`，因此无需本地计数。
若你的 provider 不上报 usage，见[第 3 节](#3-压缩取代记忆摘要)的消息条数兜底。

## 2. 注意力窗口改由预设声明

`max_context`（输入预算）与 `max_output`（响应预留）现在是 `ModelPreset`
的字段。`LLMConfig.session_tokens_windows` 与 `LLMConfig.max_tokens` 仅在预设
未设置时作为兜底。

```python
# 之前：所有模型共用一个全局数字
config.llm.session_tokens_windows = 128_000
config.llm.max_tokens = 4_000

# 之后：由模型自己声明窗口
preset = ModelPreset(
    model="deepseek-chat",
    name="deepseek",
    api_key="sk-...",
    max_context=64_000,
    max_output=8_000,
)
```

两个辅助函数负责把预设字段与配置合成一个确定值，调用方无需判断 `None`：

```python
from amrita_core.types.preset import resolve_max_context, resolve_max_output

window = resolve_max_context(preset, config)
budget = resolve_max_output(preset, config)
```

如果你此前把 `config.llm.max_tokens` 直接传给 provider 请求，请改用
`resolve_max_output(preset, config)`。内置适配器已经这样做了。

### 新的默认值

`max_output` 现在默认为 `28000`，`LLMConfig.max_tokens` 默认为 `10000`。原先
`1000` 的全局默认值偏小：推理模型可能把全部预算花在思考上而返回空答案，压缩摘要也
可能返回空内容从而静默跳过折叠。

`max_tokens` 现在只是最后兜底——只有当预设显式设置 `max_output=None` 时才会用到，
因此需要不同上限的模型在自己的预设里声明即可。

## 3. 压缩取代记忆摘要

`enable_memory_abstract` 现在叫 `context_strategy`（中间曾短暂叫
`enable_compaction`）。原先的比例/阈值组合被“窗口比例 + 消息条数兜底”取代：

```python
# 之前
config.llm.enable_memory_abstract = True
config.llm.memory_abstract_proportion = 0.5
config.llm.memory_abstract_threshold = 4000

# 之后
config.llm.context_strategy = "compact"  # "compact" | "slide" | "none"
config.llm.compaction_trigger_ratio = 0.9  # 占注意力窗口的比例
config.llm.slide_target_ratio = 0.7  # "slide" 下裁剪回这个比例
config.llm.memory_length_limit = 200  # 消息条数兜底，0 = 关闭
config.llm.enable_overflow_recovery = True  # 溢出时压缩并重试
```

阈值不再需要你手工维护：`ContextCompactor` 由 `max_context` ×
`compaction_trigger_ratio` 推导，因此跟随模型。压缩在两条触发线中先到者触发：

- provider 为上一次请求上报的 prompt 大小达到阈值
- 历史达到 `memory_length_limit` 条

第二条触发线存在的原因是第一条依赖 provider 上报 usage。除非你使用的所有
provider 都会上报 usage，否则请保留 `memory_length_limit` 的默认值。

摘要存放在 `MemoryModel.abstract`，由 train 模板渲染回系统指令，因此永远不会
进入消息列表。

### `MemoryLimiter` 已移除

`chatmanager.MemoryLimiter` 被删除，它的三项职责现已分散到别处：

| 职责                   | 现由谁负责                                            |
| ---------------------- | ----------------------------------------------------- |
| 限制消息条数           | `LLMConfig.memory_length_limit`（双触发）             |
| 为纯文本模型拍平内容块 | `NORMALIZE_MESSAGES` 节点（`llm.enable_multi_modal`） |
| 折叠长历史             | `ContextCompactor` / `COMPACT` 节点                   |

注意 `LLMConfig.enable_multi_modal` 现在由 `NORMALIZE_MESSAGES` 消费：关闭它时，
块列表形式的消息体会在请求构建前被拍平成文本。

## 4. 计费成为一等公民

新增公开类型：

- `RateConfig`——价格快照，挂载在 `ModelPreset` 上
- `BillingRecord`——单次 provider 请求的用量加上当时适用的价格
- `BillingBackend` / `NullBillingBackend`——可选的外部接收端
- `BackendSlots.billing`——承载它的槽位

```python
from decimal import Decimal

from amrita_core import ModelPreset, RateConfig

preset = ModelPreset(
    model="deepseek-chat",
    name="deepseek",
    api_key="sk-...",
    rate=RateConfig(per=1_000_000, input=Decimal("0.27"), output=Decimal("1.10")),
)
```

记录累积在 `MemoryModel.billing`，这是默认持久化路径——只有在需要把它们镜像到
外部成本存储时，才需要计费后端。`SessionUsageProxy` 取代了旧的
`UsageRegistry` 系列，由 `ChatObject` 按运行创建。

AmritaCore 不计算货币金额；它保存价格与 token 计数，由消费方自行推导成本。
`DatabackendOptions.skip_billing_commit` 开关见
[BillingBackend](api-reference/classes/BillingBackend.md)。

## 5. `StateContext` 已移除

`StateContext` 自 0.10 起被弃用，现在已删除。

```python
# 之前
from amrita_core import StateContext

ctx = StateContext(session_id="s1")
chat = ChatObject(train=train, user_input="hi", context=ctx)
sid = chat.state.session_id

# 之后
chat = ChatObject(train=train, user_input="hi", session_id="s1")
sid = chat.session_id
```

- `ChatObject(context=...)` 已移除。`session_id` 现在是**必填**：
  不带它构造 `ChatObject` 会抛
  `ValueError("session_id must be provided")`
- `chat.state`（读写器）已移除
- `LegacyBackend(ctx=...)` 已移除；`LegacyBackend()` 不接受参数

该访问器原先暴露内容的替代方案：

| 旧写法                   | 新写法                       |
| ------------------------ | ---------------------------- |
| `chat.state.session_id`  | `chat.session_id`            |
| `chat.state.memory`      | `chat.data`（`MemoryModel`） |
| `chat.state.ability`     | `chat._di_ability.ability`   |
| `chat.state`（整个对象） | 按需读取各个 `_di_*` 上下文  |

## 6. `HybridReActAgentStrategy` 已移除

已弃用的 `HybridReActAgentStrategy`（XML 渲染，`agent-mixed`）被删除。请使用
`ReActAgentStrategy`，它以 OpenAI 兼容的 `assistant(tool_calls)` + `tool`
消息结构配对工具调用与其结果。

```python
# 之前
from amrita_core.builtins.agent import HybridReActAgentStrategy

# 之后
from amrita_core.builtins.agent import ReActAgentStrategy
```

`HYBRID_TEMPLATE` 常量随之移除。`agent-mixed` **类别**不受影响：它由
`ReActAgentStrategy.get_category()` 返回，工作流据此把策略派发进 agent 循环
（见 [Agent 策略](concepts/agent-strategy.md)）。

## 7. 序列化需要 `mode="json"`

`RateConfig.input` / `.output` 是 `Decimal`。因此 `model_dump()` 返回的是
`Decimal` 对象，`json.dump` 无法序列化：

```python
# 之前
json.dump(memory.model_dump(), f)

# 之后
json.dump(memory.model_dump(mode="json"), f)
```

`ModelPreset.save()` 已经这样做。你自己持久化 `MemoryModel` 或 `ModelPreset`
的地方也需要同样修改。

## 8. 工具参数会被校验

`call_tool()` 现在会在运行 handler 之前，把模型产生的参数与工具的参 schema 做
校验。违反声明会抛 `ValidationError`，Agent 循环把它作为 `ERR: ...` 工具结果
回传给模型。

大多数工具无需改动，但有两个行为值得知道：

- 以前能收到不合规范参数的工具，现在会收到错误结果。如果你的 handler 有意容忍
  坏输入，要么在内部自行校验，要么用
  `FunctionConfig(validate_tool_arguments=False)` 关掉该检查。
- 被省略的参数保持省略，因此 handler 上的 Python 默认值仍然生效。

同一层还提供了投影方向，因此可以用一个 Pydantic 模型描述工具，而不必手写
schema：

```python
from pydantic import BaseModel, Field

from amrita_core.tools.manager import on_tools
from amrita_core.tools.schema import function_definition_from_pydantic


class LookupArgs(BaseModel):
    """Look a user up by id."""

    user_id: int = Field(description="Numeric user id", ge=1)


@on_tools(function_definition_from_pydantic(LookupArgs, name="lookup"))
async def lookup(args: dict) -> str:
    return f"user {args['user_id']}"
```

`simple_tool` 的类型注解解析器已移到 `amrita_core.tools.schema`，名为
`python_type_to_property_schema` / `pydantic_model_to_property_schema`。它以前
携带的私有名 `_python_type_to_property_schema` 已不存在。

MCP 工具也不再丢失约束：`minimum`、`maximum`、`pattern`、`minLength`、
`maxLength`、`multipleOf`、`exclusiveMinimum`、`exclusiveMaximum`、`const`、
`default` 与 `additionalProperties` 现在都会从服务器的 JSON Schema 带过来。

## 9. 三个未使用的 `SuspendEnum` 值已移除

`SuspendEnum.MEMORY_APPEND`、`SuspendEnum.FINALIZE` 与
`SuspendEnum.CALL_SINGLE_STRATEGY` 虽已声明，但从未挂接到任何节点，因此从未有
东西发出过它们。现在已删除。

实际影响只涉及**等待**它们的代码：

```python
# 之前——会永久阻塞，因为没有任何东西发出过这个标签
await chat.io_stream.wait_to_suspend(SuspendEnum.FINALIZE.value)
```

如果需要在运行结束时挂钩，请用 `COMPLETION` 事件
（[事件系统](concepts/event.md)）或 `COMMIT_MEMORY` 标签，后者挂接在真实节点
上。注意 `MEMORY_APPEND` 从来不是 `APPEND_RESPONSE` 上的标签——该节点携带的是
`SuspendEnum.MEMORY`，与 `COMPACT` 相同。

## 10. `hide` 开关已移除——请过滤流

`BuiltinAgentConfig.agent_tool_call_notice` 与 `agent_reasoning_hide` 已移除。
它们试图在框架内部决定消费者应该看到什么，而两者彼此矛盾：「开始调用」通知完全
忽略了 `agent_tool_call_notice`，因此 `"hide"` 从未真正隐藏过任何东西。

框架现在始终发出结构化事件，把展示方式留给消费者：

| 事件         | `type`            | `extra_type` |
| ------------ | ----------------- | ------------ |
| 工具调用开始 | `function_call`   | —            |
| 工具调用返回 | `function_call`   | —            |
| 推理流       | `reasoning_chunk` | `cot_chunk`  |

```python
# 之前
config.builtin.agent_tool_call_notice = "hide"

# 之后——不想要的自己丢掉
async for msg in chat.io_stream.get_response_generator():
    if getattr(msg, "metadata", {}).get("type") == "function_call":
        continue
```

`agent_reasoning_hide` 在框架中从未被读取过，因此移除它不改变任何运行时行为。

## 11. `full_response()` 只返回答案

`ChatObject.full_response()` 以前会把流中的每个条目都拼接起来，包括
`MessageWithMetadata` 事件。由于推理模型把思考以 `reasoning_chunk` 事件流式输出，
返回的字符串会以模型的推理开头、以答案结尾。

现在它只收集答案 chunk，结果与响应对象的 `content` 一致，而不再长出约十倍。

流本身没有变化——推理仍以事件形式到达。对每个条目都调 `get_content()` 的消费者
仍然会把思考混进自己的输出；请按类型或按 `metadata["type"]` 分支（参见
[流式与回调](tutorials/streaming.md)）。

## 12. 泄漏金丝雀现在真的会运行

`builtins/hooks.py` 通过 import 副作用注册它的完成匹配器，而此前没有任何地方导入
它——`load_amrita()` 只加载 MCP 客户端。因此 cookie 守卫从未运行过。现在
`amrita_core.builtins` 会导入它。

守卫本身的两处缺口也已堵上：

- **推理内容会被扫描。** 检查原本只看答案，因此在思考里引用金丝雀的模型可以通过。
  推理是模型输出的一部分且会流式送达消费者，因此现在也会检查。
- **持久化响应会被重写。** runner 会把完成事件携带的内容写入响应对象与对话历史。
  只替换流式载荷会让金丝雀仍可通过 `get_last_response()` 与下一轮上下文拿到。

已经交给流式消费者的 chunk 无法收回；追加到流中的错误载荷是本次运行失败的标记。

## 13. 压缩拥有独立的输出预算

摘要调用以前继承对话预设的输出上限。推理模型在产出任何内容之前会先花掉预算思考，
因此较小的 `max_output` 会产出空摘要，折叠静默失效。

`LLMConfig.compaction_max_tokens`（默认 `2048`）现在只为摘要调用抬高上限；设为 `0`
则回到继承预设值的行为。

同样的饥饿也会发生在普通答案上。当 provider 返回了推理但既无内容也无工具调用时，
框架现在会记录一条指明原因的警告，而不是毫无解释地返回空回复。

## 14. Anthropic 路径的内联图片已可用

Anthropic 适配器以前把每个 `ImageContent` 都翻译成 `source.type` 为 `url` 的
`image` 块。provider 接受三种 source 变体，并会拒绝以 `url` 形式发送的 `data:`
URI，因此内联图片会让整个请求以 `400 invalid url` 失败：

```python
#  修复前失败，现在可用
ImageContent(
    type="image_url",
    image_url=ImageUrl(url="data:image/png;base64,iVBORw0KGgo..."),
)
```

适配器现在根据 URL 选择变体：内联 `data:` URI 转为 `base64` source（带 media
type），其它一律保持 `url` source。外部 `http(s)` URL 此前行为就正确，未作改动。

无法转为 `base64` source 的 `data:` URI 现在会抛出 `ValueError` 而非被转发：缺少
media type、非 base64 载荷、空 body 三种情况都会响亮失败，而不是发出一个让模型
对着它从未收到的图片作答的请求。

## 下一步

[API 参考](api-reference/index.md)——完整的 1.0 接口，或
[内置能力](builtins.md)——开箱即用的东西。
