# 教程

本节将带你逐步使用 AmritaCore 构建智能体。每个教程都建立在前一个教程的基础上，并且全部使用推荐的 [`create_agent()`](../api-reference/index.md#create_agent) 工厂函数——这是最简单的入门方式。

> **注意**：这些教程中的示例仅使用公共 API。要深入了解每个步骤背后的概念，请参阅[核心概念](../concepts/index.md)部分。

## 前置条件

- Python 3.10+ 并安装了 `amrita_core`
- 一个 LLM API 端点（兼容 OpenAI、Anthropic 或任何[支持的适配器](../api-reference/index.md#backends--contexts)）
- 基本熟悉 Python 中的 `async`/`await`

## 教程路径

| 教程                                      | 你将构建的内容                                       |
| ----------------------------------------- | ---------------------------------------------------- |
| [1. 创建你的第一个 Agent](chat-object.md) | 使用 `create_agent()` 创建一个最小聊天智能体         |
| [2. 为 Agent 添加工具](tools.md)          | 使用 `@simple_tool` 和 `@on_tools` 注册可调用工具    |
| [3. 流式输出与回调](streaming.md)         | 逐 token 流式响应并挂接回调                          |
| [4. 事件与钩子](event-hooks.md)           | 使用 `@on_completion` / `@on_precompletion` 拦截管道 |
| [5. 记忆与会话](memory.md)                | 通过 `session_id` 跨轮次持久化对话历史               |

每个教程大约需要 5-10 分钟。如果你更喜欢先阅读一个独立完整示例，快速开始中的[最小示例](../getting-started/minimal-example.md)是一个很好的起点。

## 下一步

- 理解内部原理 → [核心概念](../concepts/index.md)
- 实现特定功能 → [操作指南](../how-to/function-implementation.md)
- 探索挂起/恢复和工作流 → [高级主题](../advanced/index.md)
