# ContextCompactor

历史管理策略对象：触发点相对模型注意力窗口的位置、触发后跑哪种策略，以及裁剪后的历史如何被应用。

## 描述

`ContextCompactor` 是一个 dataclass，在**每个使用点**由当前 config、preset 与运行账本构建，因此触发阈值始终反映真正被调用的那个模型。它是唯一知道如何裁剪历史的地方；工作流节点与 agent 循环都驱动同一个对象，这就是「一个模型由一个阈值描述」的原因。

两个消费方：

| 调用点                            | 时机                     |
| --------------------------------- | ------------------------ |
| `MANAGE_CONTEXT` 节点             | 轮边界，在请求构建之前   |
| `ReActAgentStrategy` 的 Step 之间 | agent 循环内的 Step 边界 |

`config.llm.context_strategy` 决定策略：

| 取值        | 效果                                                                                             |
| ----------- | ------------------------------------------------------------------------------------------------ |
| `"compact"` | 把最旧的一段折叠成摘要，存放在 [`MemoryModel.abstract`](MemoryModel.md)                             |
| `"slide"`   | 直接丢弃最旧的消息——裁到 `slide_target_ratio` × `budget`；没有可用测量值时裁到 `memory_length_limit` 条                                         |
| `"none"`    | 完全不管理——历史一直增长，直到 provider 拒绝请求                                                   |

`"compact"` 下摘要由 train 模板渲染回系统指令。不会向消息列表注入任何内容，因此 provider 的消息顺序规则不受影响。

```mermaid
flowchart LR
    A[MemoryModel.messages] -->|在最新 user 消息处切分| B[prefix]
    A --> C[tail]
    B -->|总结，并与 memory.abstract 合并| D[memory.abstract]
    C --> E[memory.messages]
    D --> F[train 模板渲染 SUMMARY]
```

```mermaid
flowchart LR
    A[MemoryModel.messages] -->|按已上报 prompt 大小加权| B[最旧的消息]
    B -->|删除| C[memory.messages]
```

## 字段

- `config` ([AmritaConfig](AmritaConfig.md))：必填。提供 `context_strategy`、`compaction_trigger_ratio`、`slide_target_ratio` 与 `memory_length_limit`
- `preset` ([ModelPreset](ModelPreset.md) | None)：其窗口驱动阈值。为 `None` 时回退到 `LLMConfig.session_tokens_windows`
- `usage` (SessionUsageProxy | None)：运行账本，使总结调用本身也像普通请求一样被计费
- `instruction` (str)：交给总结器的 system prompt，默认为 `ABSTRACT_INSTRUCTION`

## 属性

### `strategy -> Literal["compact", "slide", "none"]`

直接读取 `config.llm.context_strategy`。

### `enabled -> bool`

是否存在任何生效的策略——即 `strategy != "none"`。

### `budget -> int`

输入 token 预算：经 `resolve_max_context` 取预设的 `max_context`，否则取 `config.llm.session_tokens_windows`。

### `threshold -> int`

`int(budget * config.llm.compaction_trigger_ratio)`。由注意力窗口推导，因此触发点跟随模型，而不是一个人工维护的全局数字。

### `slide_target -> int`

`int(budget * config.llm.slide_target_ratio)`。必须小于 `threshold`，否则裁剪后会立刻落回触发线上，每次请求都重新裁剪。该约束由 [LLMConfig](LLMConfig.md) 的校验器强制，而非只写在文档里。

### `message_limit -> int`

`config.llm.memory_length_limit`。token 触发依赖 provider 上报 usage；该兜底覆盖从不上报的网关，以及超大窗口。

## 方法

### `needs_management(memory: MemoryModel | None) -> bool`

判断 `memory` 是否已超出预算、该跑当前配置的策略。两条触发线先到者生效：

- provider 为上一次请求上报的 prompt 大小（`memory.usage.prompt_tokens`）达到 `threshold`
- 历史达到 `message_limit` 条

当 `strategy` 为 `"none"`、`memory` 为 `None`，或策略无事可做时返回 `False`。

### `should_compact(memory: MemoryModel | None) -> bool`

`needs_management(memory)` 限定到 `"compact"` 策略——`"slide"` 裁剪绝不能触发一次摘要调用。

### `async summarize(prefix, previous: str = "") -> str`

总结 `prefix`；当给出 `previous` 时，把它并入 `<EXISTING_SUMMARY>` 块。返回去掉首尾空白的摘要；模型没有产出可用内容时返回空字符串。

### `async fold(messages, previous: str = "") -> CompactionResult | None`

总结可折叠的前缀并返回存活的历史。

**原子性**：摘要先产出，在拿到非空摘要之前不返回任何东西，因此总结失败会让调用方的历史保持原样。无可折叠内容或模型未返回摘要时返回 `None`。

### `async compact(memory: MemoryModel) -> bool`

就地折叠 `memory`。成功后前缀被丢弃、`abstract` 被替换、实测 usage 被清空，以便下次请求重新度量。返回是否发生了折叠。

### `slide(messages, reported: int | None = None) -> int`

把最旧的消息丢到历史重新装得下为止。`reported`（provider 上报的 prompt 规模）可用且不低于 `threshold` 时裁到 `slide_target`；没有可用测量值——网关不上报 usage，或数值低于触发线——则按 `memory_length_limit` 条裁剪，因为这条触发线不依赖 provider。就地修改 `messages`，返回丢弃的条数（没动则为 `0`）。

`reported` 是 provider 为这批消息产生的 payload 实测的 prompt 大小。全程不涉及分词器：每条消息在 `reported` 中的占比按渲染后文本长度归一化估算，因此权重求和会回到实测值。

## `split_history(messages) -> tuple[list, list]`

模块级辅助函数，把历史切成可折叠前缀与保留尾部。切点落在**最新的 `user` 消息**上，因此尾部总是从干净的轮次开始，assistant 的工具调用永远不会与其工具结果分离。无可折叠内容时返回 `([], messages)`。

这正是「在 Step 边界折叠是安全的」的原因：切点永远不会落在 tool-call/result 配对中间。

## `CompactionResult`

```python
@dataclass
class CompactionResult:
    messages: CONTENT_LIST_TYPE  # 存活的历史，从干净的轮次边界开始
    summary: str  # 替换被折叠前缀的摘要
```

## 相关

- [MemoryModel](MemoryModel.md)——`abstract` 与 `usage` 所在
- [LLMConfig](LLMConfig.md)——`context_strategy` / `compaction_trigger_ratio` / `slide_target_ratio` / `memory_length_limit` 开关
- [ModelPreset](ModelPreset.md)——`max_context`，阈值所依据的窗口
