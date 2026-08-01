# 最小示例

## 5 分钟快速上手

这是一个最小示例，展示如何使用简化的 `create_agent` 函数开始使用 AmritaCore：

```python
import asyncio
from amrita_core import create_agent, minimal_init

async def minimal_example():
    # 在创建 agent 之前初始化 AmritaCore
    await minimal_init()
    # 用最少参数创建 agent
    agent = create_agent(
        "https://api.example.com",   # 替换为你的 API URL
        "your-api-key",              # 替换为你的 API key
        model="gpt-4",               # 替换为你想要的模型
        model_config={"temperature": 0.7}
    )
    # 获取一个 chat object 用于交互
    chat = agent.get_chatobject("Hello, what can you do?")

    # 执行交互并获取响应
    async with chat.begin():
        response = await chat.full_response()
        await chat  # 等待任务完成后再退出
        print(response)

# 运行示例
if __name__ == "__main__":
    asyncio.run(minimal_example())
```

## 代码示例说明

在这个最小示例中：

1. 使用 `minimal_init()` 在创建 agent 之前初始化 AmritaCore
2. 使用 `create_agent()` 仅需必要参数（URL 和 API key）即可创建 agent
3. `create_agent` 函数自动处理初始化、配置和预设创建
4. 调用 `agent.get_chatobject()` 获取特定交互的 `ChatObject` 实例
5. 使用 `chat.begin()` 执行交互并获取完整响应

### 理解 ChatObject

`ChatObject` 是 AmritaCore 中细粒度的标准接口，提供对单次对话交互的完整控制。虽然 `create_agent` 为常见用例提供了高级简化 API，但 `ChatObject` 让你可以访问所有底层功能，包括：

- 对会话管理的直接控制
- 自定义上下文和记忆处理
- 高级配置选项
- 完整访问事件系统和钩子
- 对流式行为的精细控制

对于大多数基本用例，`create_agent` 已足够且更简单。然而，当你需要精细控制或想要实现自定义行为时，可以直接使用 `ChatObject`。

## 运行与调试

运行示例：

1. 安装 AmritaCore
2. 将 `https://api.example.com` 和 `your-api-key` 替换为实际值
3. 使用 `python your_script.py` 执行脚本

如需调试，可在代码中配置 logger 以启用详细日志。
