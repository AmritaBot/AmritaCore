# 创建你的第一个 Agent

在本教程中，你将使用 [`create_agent()`](../api-reference/index.md#create_agent) 工厂函数创建一个最小聊天智能体。

## 1. 初始化 AmritaCore

在创建智能体之前，先初始化框架。[`minimal_init()`](../api-reference/index.md#minimal_init) 应用全局配置，如果启用了 MCP，还会加载 MCP 客户端。当你 `import amrita_core` 时，分词器和适配器已经自动注册：

```python
import asyncio

from amrita_core import minimal_init


async def main() -> None:
    await minimal_init()
```

## 2. 创建 Agent

调用 `create_agent()` 并传入你的 LLM 端点和 API 密钥。工厂函数会自动为你创建一个临时的 [ModelPreset](../api-reference/classes/ModelPreset.md)——无需管理预设：

```python
from amrita_core import create_agent

agent = create_agent(
    base_url="https://api.openai.com/v1",  # 你的 LLM API 端点
    api_key="sk-...",                       # 你的 API 密钥
    model="gpt-4o-mini",                    # 模型标识符（默认: "auto"）
    train="You are a helpful assistant.",   # 可选的系统提示
)
```

你还可以通过 `model_config`（字典或 [ModelConfig](../api-reference/classes/ModelConfig.md) 对象）传入模型调优参数：

```python
agent = create_agent(
    base_url="https://api.openai.com/v1",
    api_key="sk-...",
    model="gpt-4o-mini",
    model_config={
        "temperature": 0.7,
        "max_tokens": 1024,
    },
)
```

## 3. 发送消息

`create_agent()` 返回一个 [AgentRuntime](../api-reference/classes/AgentRuntime.md)。调用 `agent.get_chatobject(user_input)` 创建一个绑定到智能体配置的 [ChatObject](../api-reference/classes/ChatObject.md)，然后使用 `async with chat.begin()` 运行它：

```python
async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        train="You are a helpful assistant.",
    )

    chat = agent.get_chatobject("Hello! What can you do?")
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat  # 等待任务完成——退出会取消它
    print("\n")
```

> ⚠️ **重要**：退出 `async with` 代码块会终止内部任务而不是等待它完成。请始终在代码块内 `await chat` 让响应完成。

## 4. 运行

```bash
python your_script.py
```

你应该能在终端中看到模型的流式回复。

## 刚刚发生了什么

- `create_agent()` 从 `base_url` / `api_key` / `model` 构建了一个临时 `ModelPreset`，并围绕它构建了一个 [AgentRuntime](../api-reference/classes/AgentRuntime.md)
- `get_chatobject()` 创建了一个 `ChatObject`，连接到该预设、智能体的系统提示（`train`）和一个新的 `session_id`
- `chat.begin()` 执行了 [ReAct 智能体策略](../concepts/agent-strategy.md)（默认），并通过 `io_stream` 流式传输响应

## 下一步

- [为 Agent 添加工具](tools.md)，让你的智能体可以调用函数
- [流式响应与回调](streaming.md)
- 在[核心概念](../concepts/index.md)中了解底层发生了什么
