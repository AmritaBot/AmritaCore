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

## 3. 压缩取代记忆摘要

`enable_memory_abstract` 改名为 `enable_compaction`。原先的
比例/阈值组合被“窗口比例 + 消息条数兜底”取代：

```python
# 之前
config.llm.enable_memory_abstract = True
config.llm.memory_abstract_proportion = 0.5
config.llm.memory_abstract_threshold = 4000

# 之后
config.llm.enable_compaction = True
config.llm.compaction_trigger_ratio = 0.9  # 占注意力窗口的比例
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

## 下一步

[API 参考](api-reference/index.md)——完整的 1.0 接口，或
[内置能力](builtins.md)——开箱即用的东西。
