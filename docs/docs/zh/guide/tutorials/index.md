# 教程

本节带你**一步一步**用 AmritaCore 构建 agent。每个教程建立在前一个之上，
只使用公共 API——无需了解内部实现。

## 前置要求

- Python 3.10+ 且已安装 `amrita-core`（见[快速开始](../getting-started/index.md)）
- 一个 LLM API 端点（OpenAI 兼容或 Anthropic）
- 熟悉 Python `async`/`await`

## 教程路径

| #   | 教程                                   | 你将构建                                             |
| --- | -------------------------------------- | ---------------------------------------------------- |
| 1   | [创建你的第一个 Agent](chat-object.md) | 用 `create_agent()` 和 `ChatObject` 的最小对话 agent |
| 2   | [给 Agent 添加工具](tools.md)          | 用 `@simple_tool` 和 `@on_tools` 注册可调用工具      |
| 3   | [流式与回调](streaming.md)             | 逐 token 流式、读取元数据、使用回调                  |
| 4   | [事件与钩子](event-hooks.md)           | 用生命周期事件拦截管线                               |
| 5   | [记忆与会话](memory.md)                | 用 `session_id` 持久化对话历史                       |

每个教程约 5–10 分钟。已经熟悉？跳转到
[核心概念](../concepts/index.md) 理解内部，或
[扩展与集成](../extensions-integration/index.md) 接入自己的工具、适配器与 MCP 服务器。
