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

| 上下文               | 承载                        |
| -------------------- | --------------------------- |
| `SessionMetadata`    | 会话/流 id、时间戳          |
| `MemoryContext`      | 运行时记忆                  |
| `AbilityState`       | 配置、preset、后端槽位      |
| `GeneralInput`       | 用户输入、train、模板       |
| `WorkingState`       | `SendMessageWrap`           |
| `RespState`          | 响应 + 用量                 |
| `AgentLoopState`     | 策略、调用计数、`run_state` |
| `StrategyPayload`    | 策略工厂                    |
| `DatabackendOptions` | 后端获取/提交跳过标志       |

> 用 AmritaSense 的术语，这是标准的依赖注入机制——一般规则见
> [sense.amritabot.com](https://sense.amritabot.com)。

## 两篇深入

| 页面                        | 覆盖                                                         |
| --------------------------- | ------------------------------------------------------------ |
| [数据后端](data-backend.md) | `AbilityBackend` / `MemoryBackend` 接口与如何编写自己的后端  |
| [记忆模型](data-memory.md)  | `MemoryModel`、加载/提交生命周期、遗留 `StateContext` 访问器 |

## 下一步

[扩展与集成](../extensions-integration/index.md)——适配器、工具、MCP 与
Tokenizer。
