# 最小示例

## 2.2.1 5分钟快速入门

这是一个使用简化的 `create_agent` 函数的最小示例，帮助您开始使用 AmritaCore：

```python
import asyncio
from amrita_core import create_agent, minimal_init

async def minimal_example():
    # 使用最少参数创建一个 agent
    await minimal_init()
    agent = create_agent(
    "https://api.example.com", # Replace with your API URL
    "your-api-key", # Replace with your API key
    model="gpt-4", # Replace with your desired model
    model_config={"temperature": 0.7}
    )
    
    # 获取用于交互的聊天对象
    chat = agent.get_chatobject("你好，你能做什么？")
    
    # 执行交互并获取响应
    async with chat.begin():
        print(await chat.full_response())

# 运行示例
if __name__ == "__main__":
    asyncio.run(minimal_example())
```

## 2.2.2 代码示例说明

在这个最小示例中：

1. 我们使用 `create_agent()` 仅用必要的参数（URL 和 API 密钥）创建一个 agent
2. `create_agent` 函数自动处理初始化、配置和预设创建
3. 我们调用 `agent.get_chatobject()` 获取特定交互的 `ChatObject` 实例
4. 我们使用 `chat.begin()` 执行交互并获取完整响应

### 理解 ChatObject

`ChatObject` 是 AmritaCore 中的细颗粒度标准接口，为单个聊天交互提供完全控制。虽然 `create_agent` 为常见用例提供了高级、简化的 API，但 `ChatObject` 让您可以访问所有底层功能，包括：

- 直接控制会话管理
- 自定义上下文和记忆处理
- 高级配置选项
- 完全访问事件系统和钩子
- 详细控制流式行为

对于大多数基本用例，`create_agent` 已经足够且使用起来简单得多。但是，当您需要细颗粒度控制或想要实现自定义行为时，可以直接使用 `ChatObject`。

## 2.2.3 运行和调试

要运行示例：

1. 安装 AmritaCore
2. 将 `YOUR_API_ENDPOINT` 和 `YOUR_API_KEY` 替换为实际值
3. 使用 `python your_script.py` 执行脚本

要进行调试，您可以通过在代码中配置日志记录器来启用详细日志。
