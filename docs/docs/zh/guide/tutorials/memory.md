# 记忆与会话

AmritaCore 中的每个对话都属于一个**会话**，由 `session_id` 标识。在本教程中，你将在多个轮次中重用同一个会话，以便智能体能记住上下文，并为长对话启用记忆摘要。

## 1. 会话 ID

当你创建一个智能体时，会为你生成一个随机的 `session_id`。通过 `create_agent(..., session_id=...)` 传入你自己的来控制智能体与哪个会话对话：

```python
import asyncio

from amrita_core import create_agent, minimal_init


async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        session_id="my-chat-session",  # 在多个轮次中重用此 ID
        train="你是一个有帮助的助手。",
    )

    # 第 1 轮：智能体学到了一些东西
    chat = agent.get_chatobject("我的名字是 Alice。")
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat  # 等待任务完成——退出会取消它
    print("\n")

    # 第 2 轮：同一个智能体，同一个会话——智能体仍然知道名字
    chat2 = agent.get_chatobject("我的名字是什么？")
    async with chat2.begin():
        async for message in chat2.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat2  # 等待任务完成——退出会取消它
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
```

会话的记忆由[数据后端](../concepts/data-backend.md)加载和提交——默认是 `LegacyBackend`，它将记忆存储在进程内的全局容器中。不同的 `session_id` 获得隔离的记忆。

## 2. 多个 Agent，同一会话

由于 `session_id` 存在于运行时上，使用相同 `session_id` 创建的两个智能体会共享对话历史：

```python
agent_a = create_agent(base_url=..., api_key=..., session_id="shared-session")
agent_b = create_agent(base_url=..., api_key=..., session_id="shared-session")
```

这对于拆分职责（例如不同的工具或提示）同时保持一个对话线程非常有用。

## 3. 记忆摘要

长对话会无限增长。启用**记忆抽象**，以便 AmritaCore 在上下文变长时自动摘要旧消息：

```python
from amrita_core import create_agent
from amrita_core.config import LLMConfig

agent = create_agent(
    base_url="https://api.openai.com/v1",
    api_key="sk-...",
    model="gpt-4o-mini",
    model_config={"temperature": 0.7},
)

# 在全局配置上启用摘要
from amrita_core.config import get_config, set_config

config = get_config()
config.llm.enable_memory_abstract = True
config.llm.memory_abstract_proportion = 0.15  # 在达到限制时摘要约 15% 的历史
set_config(config)
```

你还可以使用 `memory_length_limit`（记忆上下文中消息的最大数量）来限制保留多少历史。

## 4. 刚刚发生了什么

- `session_id` 限定对话记忆的范围；重用它则继续对话
- `get_chatobject()` 创建一个 `ChatObject`，它从后端获取 `session_id` 的记忆，并在运行后将其提交回去
- `LLMConfig` 的记忆设置（`enable_memory_abstract`、`memory_abstract_proportion`、`memory_length_limit`）控制自动摘要和上下文修剪

## 下一步

- 深入了解：[数据后端](../concepts/data-backend.md) 和 [数据容器](../concepts/data-containers.md)
- [实现特定功能](../how-to/function-implementation.md)
- [探索高级主题](../advanced/index.md)
