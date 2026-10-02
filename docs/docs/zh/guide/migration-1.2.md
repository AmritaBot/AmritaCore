# 迁移指南：1.1 → 1.2

AmritaCore 1.2 把历史管理变成了一条显式**策略**。原先用来开关它的布尔值已被删除，
随之删除的还有两个只在「策略唯一」时才说得通的名字。本页列出全部破坏性变更及其
替代方案。

## 一览表

| 移除 / 改名                     | 替代                                                               |
| ------------------------------- | ------------------------------------------------------------------ |
| `LLMConfig.enable_compaction`   | `LLMConfig.context_strategy`（`"compact"` / `"slide"` / `"none"`） |
| `LLMConfig.auto_retry`          | （无——框架从未读取过它）                                           |
| `COMPACT_HISTORY`（预组合管线） | `MANAGE_HISTORY`                                                   |
| `COMPACT`（工作流节点）         | `MANAGE_CONTEXT`                                                   |
| `should_compact`（节点断言）    | `should_manage_context`                                            |

## 1. 历史是一条策略，不是一个开关

`enable_compaction` 是个布尔值，关掉它历史就无界增长，直到 provider 因超出窗口
拒绝请求。取而代之的 `context_strategy` 说明「超预算后该做什么」：

```python
# 之前
config.llm.enable_compaction = True

# 之后
config.llm.context_strategy = "compact"  # "compact" | "slide" | "none"
```

| 取值        | 效果                                                                                    |
| ----------- | --------------------------------------------------------------------------------------- |
| `"compact"` | 把最旧的一段折叠成摘要，存放在 `MemoryModel.abstract`。每次裁剪多一次调用，要点得以保留 |
| `"slide"`   | 直接丢弃最旧的消息，裁剪到 `slide_target_ratio` × 窗口。不额外调用，尾部保持原文        |
| `"none"`    | 什么都不做——历史一直增长，直到 provider 拒绝请求                                        |

触发线没有变：provider 为上一次请求上报的 prompt 达到 `compaction_trigger_ratio` ×
预设 `max_context`，或历史达到 `memory_length_limit` 条。

`"none"` 同时会禁用溢出恢复——没有策略能缩小历史时，`ContextOverflowError` 之后
重试只会以同样方式失败。

## 2. `slide` 不花钱，但会遗忘

新的 `"slide"` 策略面向「早期轮次可以丢弃」的会话：长时间的工具调用运行中，
每次裁剪都付一次摘要调用的代价比丢掉记录更糟。

它不需要分词器。每条消息在已上报 prompt 大小中的占比按渲染后长度归一化估算，
因此权重求和会回到实测值，裁剪落点由 `slide_target_ratio` × `max_context` 决定：

```python
config.llm.context_strategy = "slide"
config.llm.slide_target_ratio = 0.7  # 必须小于 compaction_trigger_ratio
```

切点不会落在轮次中间，也不会留下「声明它的调用已被删除」的游离工具结果，
因此裁剪后的负载依然能通过网关校验。

请让 `slide_target_ratio` 小于 `compaction_trigger_ratio`。两者相等会把历史裁剪回
触发线上，于是每次请求都要重新裁剪。

## 3. `auto_retry` 已移除

`LLMConfig.auto_retry` 从未被框架读取——真正决定重试的是 `max_retries` 与
`max_fallbacks`。设置它没有任何效果，因此直接删除，而不是留着一个幌子。
删掉那行赋值即可，没有替代项。

## 4. 节点与管线名一并调整

这两个名字都假定了唯一的策略就是折叠，而这已不再成立：

| 之前                    | 之后                         |
| ----------------------- | ---------------------------- |
| `COMPACT` 节点          | `MANAGE_CONTEXT` 节点        |
| `COMPACT_HISTORY` 图    | `MANAGE_HISTORY` 图          |
| `should_compact` 节点   | `should_manage_context` 节点 |

`ContextCompactor.should_compact()` 仍然存在——它是新断言 `needs_management()` 在
`"compact"` 上的收窄，供只想知道「这次会不会折叠」而非「这条策略要不要动手」的
调用方使用。

只有在你自行组合工作流、或对管线做断言时才会受影响；传 `workflow=None` 或使用
内置的 `SIMPLE_*` 图不受影响。

## 下一步

[API 参考](api-reference/index.md)——当前接口全貌，或
[迁移指南：0.13 → 1.0](migration.md)——上一个破坏性版本。
