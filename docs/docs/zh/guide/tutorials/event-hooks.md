# 事件与钩子

AmritaCore 暴露了一个事件系统，允许你拦截处理管道。在本教程中，你将附加在 LLM 完成前后运行的钩子。

## 1. 使用 `@on_completion` 响应完成事件

[`@on_completion`](../api-reference/index.md#on_completion) 注册一个在模型完成生成后运行的处理函数。处理函数接收一个 [CompletionEvent](../api-reference/classes/CompletionEvent.md)：

```python
import asyncio

from amrita_core import create_agent, minimal_init, on_completion
from amrita_core.hook.event import CompletionEvent


@on_completion().handle()
async def log_completion(event: CompletionEvent) -> None:
    print(f"[完成] 模型说: {event.get_model_response()}")


async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        train="你是一个有帮助的助手。",
    )

    chat = agent.get_chatobject("2 + 2 等于多少？")
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat  # 等待任务完成——退出会取消它
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
```

`CompletionEvent` 在每次完成轮次中触发一次——包括单次对话中的工具调用轮次。

## 2. 使用 `@on_precompletion` 的预完成钩子

[`@on_precompletion`](../api-reference/index.md#on_precompletion) 在请求发送到 LLM **之前**运行，允许你检查或修改传出的消息。处理函数接收一个 [PreCompletionEvent](../api-reference/classes/PreCompletionEvent.md)：

```python
from amrita_core import on_precompletion
from amrita_core.hook.event import PreCompletionEvent


@on_precompletion().handle()
async def log_request(event: PreCompletionEvent) -> None:
    print(f"[请求] 正在向模型发送 {len(event.messages)} 条消息")
```

## 3. 使用 `@on_event` 自定义事件

对于应用程序特定的事件，使用 [`@on_event`](../api-reference/index.md#on_event) 并传入你自己的事件类型：

```python
from amrita_core import on_event


@on_event("my_app:user_login").handle()
async def handle_login(event) -> None:
    print("用户登录:", event)
```

## 4. 刚刚发生了什么

- `@on_completion` / `@on_precompletion` 使用内置的 [EventTypeEnum](../api-reference/index.md#events--hooks)（`COMPLETION` / `BEFORE_COMPLETION`）包装了通用的 [`on_event`](../api-reference/index.md#on_event)
- 处理函数由 `MatcherManager`（由 `amrita-sense` 包提供）调度，支持可选的 `priority` 和 `block` 行为
- 完整的事件目录和回退处理参见[核心概念：事件系统](../concepts/event.md)

## 下一步

- [管理记忆和会话](memory.md)
- 深入了解：[核心概念：事件系统](../concepts/event.md)
