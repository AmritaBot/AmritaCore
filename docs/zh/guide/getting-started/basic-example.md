# 基础示例

## 2.3.1 完整功能演示

让我们看一个更完整的示例，演示如何使用简化的 `create_agent` 接口实现上下文记忆和多轮交互：

```python
"""
Basic Example for AmritaCore - A simple demonstration of core functionality.

This example shows how to create an agent, interact with it, and maintain
conversation context across multiple turns using the new unified API.
"""

import asyncio

from amrita_core import create_agent  # Main entry point
from amrita_core.logger import logger  # Optional logging


async def basic_example():
    """
    Basic example demonstrating core functionality with the new agent API.
    Shows agent creation, streaming responses, and automatic context retention.
    """
    print("🚀 Starting AmritaCore Basic Example (New API)")
    print("-" * 50)

    # Create an agent with minimal configuration
    # All necessary defaults (system prompt, context handling) are built-in
    agent = create_agent(
        base_url="https://api.example.com",           # Your API endpoint
        api_key="your-api-key",                        # Your API key
        model="gpt-3.5-turbo",                         # Model name
        model_config={                                  # Optional model parameters
            "temperature": 0.7,
            "stream": True,                             # Enable streaming
        }
    )
    logger.info("✅ Agent created successfully.")

    print("💬 Starting a sample conversation:")
    print()

    # Example 1: First interaction
    user_input = "Hello! Can you tell me what AmritaCore is?"

    print(f"👤 User: {user_input}")

    # Get a chat object for this user input
    chat = agent.get_chatobject(user_input)

    print("🤖 Assistant: ", end="")

    # Stream the response token by token
    async with chat.begin():
        async for message in chat.get_response_generator():
            # message can be a string or a Message object
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")

    print("\n")  # New line after response

    # Example 2: Follow-up question – context is automatically retained by the agent
    follow_up = "Can you explain its main features?"

    print(f"👤 User: {follow_up}")

    # Simply create another chat object with the same agent
    chat2 = agent.get_chatobject(follow_up)

    print("🤖 Assistant: ", end="")

    async with chat2.begin():
        async for message in chat2.get_response_generator():
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")

    print("\n")  # New line after response

    print("🎉 Basic example completed successfully!")
    print("-" * 50)
    print("💡 Key concepts demonstrated:")
    print("   • Agent creation with create_agent()")
    print("   • Obtaining chat objects via agent.get_chatobject()")
    print("   • Streaming responses")
    print("   • Automatic context retention across turns")
    print("   • Built‑in default system prompt")


async def minimal_example():
    """
    A minimal example showing the essential steps to run AmritaCore.
    """
    print("\n🧪 Minimal Example")
    print("-" * 30)

    # Create an agent with just the required parameters
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-4",
        model_config={"temperature": 0.7}
    )

    # Get a chat object and get the full response (non‑streaming)
    chat = agent.get_chatobject("你好，你能做什么？")

    async with chat.begin():
        response = await chat.full_response()

    print(f"💬 Response: {response}")
    print("✅ Minimal example completed!")


if __name__ == "__main__":
    # No explicit init() needed – create_agent handles everything
    asyncio.run(basic_example())
    asyncio.run(minimal_example())

    print("\n✨ All examples completed!")
```

## 2.3.2 配置说明

新版 API 简化了配置流程：

- **创建 Agent**：`create_agent(base_url, api_key, model, model_config)` 是唯一的入口。它内部会自动设置默认的系统提示、上下文管理和模型预设。
- **模型配置**：通过 `model_config` 字典传递任何模型参数（例如 `temperature`、`stream`）。`stream` 标志控制是否使用流式响应。
- **上下文处理**：Agent 会自动保留对话历史。您**无需**手动管理 `MemoryModel` 或 `train` 消息——这些都已内置，除非您需要在外部序列化与反序列化。
- **系统提示**：提供了合理的默认系统提示。如果您需要自定义，`create_agent` 接受一个可选的 `train
` 参数。

## 2.3.3 常见问题排查

**问题**：连接到 API 端点时出现连接错误  
**解决方案**：检查 `base_url` 和 `api_key` 是否正确，并确保网络可以访问该端点。

**问题**：长对话中 Token 消耗过高  
**解决方案**：Agent 会自动应用内存摘要（如果后端启用了该功能）来总结旧消息。您也可以在 `model_config` 中调整 `max_tokens` 参数来限制响应长度。

**问题**：响应缓慢  
**解决方案**：检查网络延迟。如需更快的响应，可考虑使用较小的模型或降低 `temperature`（这会使输出更确定，稍快一些）。流式响应（`stream=True`）也能让文本更早开始显示。

**问题**：多轮对话后上下文似乎丢失  
**解决方案**：确保同一对话的所有轮次都使用**同一个 agent 实例**。每次调用 `agent.get_chatobject()` 都会自动使用 agent 的内部上下文。