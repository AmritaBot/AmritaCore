# 数据管理

数据如何在 AmritaCore 中流动：消息、记忆、后端，以及在工作流节点间传递
状态的 DI 上下文。

## 消息

| 类型              | 角色                                                               |
| ----------------- | ------------------------------------------------------------------ |
| `Message`         | 一条对话消息（role、content、`tool_calls`、`reasoning_content`）   |
| `ToolResult`      | 工具输出，与它的 `tool_call_id` 配对                               |
| `SendMessageWrap` | 工作上下文：`train` + `memory` + `user_query` + `end_messages`     |
| `UniResponse`     | 规范化 LLM 响应（content、tool_calls、`reasoning_content`、usage） |

`SendMessageWrap` 是策略修改的对象——`ctx.message.append(...)` 加到
`end_messages`，`unwrap()` 会把它们包含进下一次请求。

## DI 上下文

工作流节点通过**类型匹配注入**接收状态——节点声明参数如
`loop: AgentLoopState`，解释器注入匹配实例。关键上下文（全部由
`ChatObject` 拥有）：

| 上下文               | 承载                                               |
| -------------------- | -------------------------------------------------- |
| `SessionMetadata`    | 会话/流 id、时间戳                                 |
| `MemoryContext`      | 运行时记忆                                         |
| `AbilityState`       | 配置、preset、后端槽位                             |
| `GeneralInput`       | 用户输入、train、模板                              |
| `WorkingState`       | `SendMessageWrap`                                  |
| `RespState`          | 响应 + 用量（本次运行的 `SessionUsageProxy` 账本） |
| `AgentLoopState`     | 策略、调用计数、`run_state`                        |
| `StrategyPayload`    | 策略工厂                                           |
| `DatabackendOptions` | 后端获取/提交跳过标志                              |

> 用 AmritaSense 的术语，这是标准的依赖注入机制——一般规则见
> [sense.amritabot.com](https://sense.amritabot.com)。

## 成本核算

每一次上报 usage 的 provider 请求都会向**运行作用域**的账本
（`RespState` 上的 `SessionUsageProxy`）追加一条 `BillingRecord`。运行结束时，
这些记录被复制进 `MemoryModel.billing`，那是默认持久化路径——因此存整个
`MemoryModel` 的记忆后端已经存下了成本历史。只有当同一批记录还需镜像到
别处时，才需要 `BillingBackend`。

每条记录携带模型、预设名，以及请求时刻生效的 `RateConfig`。AmritaCore
刻意到此为止：它存下倍率与 token 计数，由消费方推导货币金额，这样后续
调价永远不会改写历史。见[数据后端](data-backend.md#三个槽位以及计费为何不同)
与 [BillingRecord](../api-reference/classes/BillingRecord.md)。

## 两篇深入

| 页面                        | 覆盖                                                                           |
| --------------------------- | ------------------------------------------------------------------------------ |
| [数据后端](data-backend.md) | `AbilityBackend` / `MemoryBackend` / `BillingBackend` 接口与如何编写自己的后端 |
| [记忆模型](data-memory.md)  | `MemoryModel`、加载/提交生命周期与历史压缩                                     |

## 下一步

[扩展与集成](../extensions-integration/index.md)——适配器、工具与 MCP。
