# 最小示例

最简完整的 AmritaCore 程序。复制、粘贴、运行。

> **你将看到**：agent 的回答逐 token 流出。循环前的三行（`minimal_init`、
> `create_agent`、`get_chatobject`）就是全部配置——其余都是 AmritaCore 在
> 替你干活。

```python
import asyncio
import os

from amrita_core import create_agent, minimal_init


async def main() -> None:
    await minimal_init()
    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key=os.environ["OPENAI_API_KEY"],
        model="gpt-4o-mini",
    )
    chat = agent.get_chatobject("Hello! Who are you?")
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
```

## 刚才发生了什么

| 行                           | 作用                               |
| ---------------------------- | ---------------------------------- |
| `minimal_init()`             | 初始化全局配置（每个进程一次）     |
| `create_agent(...)`          | 构建绑定到你端点的 `Agent` 工厂    |
| `agent.get_chatobject(text)` | 创建 `ChatObject`——对话的基本单位  |
| `chat.begin()`               | 运行工作流；agent 在此上下文内作答 |
| `get_response_generator()`   | 逐 token 流式读取响应              |

## 备注

- 使用匹配的 `base_url` + `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` 环境变量时，
  `api_key` 可省略。
- DeepSeek 等 OpenAI 兼容供应商：只改 `base_url` 和 `model` 即可。
- Anthropic？用 `protocol="anthropic"`——见[适配器](../extensions-integration/adapters.md)。

## 下一步

[基础示例](basic-example.md)——加入流式元数据、工具与会话。
