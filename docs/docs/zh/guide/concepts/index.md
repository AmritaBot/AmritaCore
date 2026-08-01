# 核心概念

本节解释 AmritaCore 背后的基本概念：每个组件是什么、为什么存在，以及各部分如何组合。如果你在寻找分步指导，请从[教程](../tutorials/index.md)开始。

## 核心概念

| 概念                                   | 涵盖内容                                                                                                   |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| [配置系统](configuration.md)           | `AmritaConfig`、`FunctionConfig`、`LLMConfig`、`CookieConfig`、`BuiltinAgentConfig`——AmritaCore 的配置方式 |
| [ChatObject——对话对象](chat-object.md) | 核心对话类、预设、流式传输、回调和记忆摘要                                                                 |
| [事件系统](event.md)                   | 处理管道中的钩子：前置完成、完成和回退事件                                                                 |
| [工具系统](tool.md)                    | 工具的定义、注册以及 agent 调用方式                                                                        |
| [Agent 策略](agent-strategy.md)        | Agent 行为的策略模式：ReAct、Hybrid ReAct、NoAction                                                        |

## 数据管理

数据层将**数据长什么样**与**数据如何存储**分离：

- [数据管理](data-management.md)——数据架构概览
- [数据容器](data-containers.md)——`Message`、`MemoryModel`、`StateContext`、工具注册表和 MCP 客户端管理器
- [数据后端](data-backend.md)——`AbilityBackend` / `MemoryBackend` 接口和 `LegacyBackend`
- [数据杂项](data-misc.md)——`ModelConfig`、`ModelPreset`、`UniResponse`、`SendMessageWrap` 和嵌入分块

## 下一步

- 想构建第一个 agent？→ [教程](../tutorials/index.md)
- 需要实现特定功能？→ [操作指南](../how-to/function-implementation.md)
- 深入了解内部机制？→ [高级](../advanced/index.md)
