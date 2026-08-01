# 流式输出与回调

AmritaCore 默认对所有响应进行流式输出。在本教程中，你将直接消费流，并切换到基于回调的风格。

## 1. 流式消费响应

每个 [ChatObject](../api-reference/classes/ChatObject.md) 都暴露 `io_stream`，其 `get_response_generator()` 会在响应块到达时逐个产出：

```python
import asyncio

from amrita_core import create_agent, minimal_init


async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        train="你是一个有帮助的助手。",
    )

    chat = agent.get_chatobject("写一首关于大海的俳句。")
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat  # 等待任务完成——退出会取消它
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
```

每个产出的元素要么是普通 `str` 块，要么是类型化的内容对象——`message.get_content()` 返回其文本。退出 `async with` 代码块会取消内部任务，因此请始终在代码块内 `await chat`。

## 2. 基于回调的消费方式

如果你更喜欢，可以注册一个回调函数，每个块都会被调用。在流上使用 `set_callback_func()`，然后 `begin()` 运行对话并驱动回调：

```python
async def response_callback(chunk) -> None:
    print(chunk if isinstance(chunk, str) else chunk.get_content(), end="")


async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        train="你是一个有帮助的助手。",
    )

    chat = agent.get_chatobject("告诉我一个关于太空的有趣事实。")
    chat.io_stream.set_callback_func(response_callback)
    chat.begin()
    await chat  # begin() 只启动任务；await 等待它完成
    print("\n")
```

## 3. 使用 `full_response()` 获取完整响应

要一次性收集完整响应（不流式），在 `begin()` 后使用 `full_response()`：

```python
async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
    )

    chat = agent.get_chatobject("法国的首都是什么？")
    chat.begin()
    response = await chat.full_response()
    print(response)
```

`full_response()` 是一次性消费者——用它**替代** `get_response_generator()`，不要两者都使用。

## 刚刚发生了什么

- `io_stream.get_response_generator()` 是一个异步生成器，实时发送块
- `set_callback_func()` 切换到推送式消费——每个块触发回调，而 `begin()` 持续运行
- `full_response()` 在执行完成后给你组装好的最终响应

## 下一步

- [使用事件拦截管道](event-hooks.md)
- [管理记忆和会话](memory.md)
- 深入了解：`amrita-sense` 包中的 [SuspendObjectStream](https://sense.amritabot.com)
