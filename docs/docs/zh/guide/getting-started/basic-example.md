# 基础示例

## 完整基础功能演示

让我们看一个更完整的示例，展示如何使用简化的 `create_agent` 接口实现上下文保持和多轮交互：

```python
"""
AmritaCore 基础示例 — 核心功能简单演示。

本示例展示如何使用新的统一 API 创建 agent、与之交互、
并在多轮对话中保持上下文。
"""

import asyncio

from amrita_core import create_agent, minimal_init   # 主入口
from amrita_sense.logging import logger             # 可选日志


async def basic_example():
    """
    基础示例：演示新 agent API 的核心功能。
    展示 agent 创建、流式响应和自动上下文保持。
    """
    print("🚀 启动 AmritaCore 基础示例（新 API）")
    print("-" * 50)

    # 在创建 agent 之前初始化 AmritaCore
    await minimal_init()
    # 用最少配置创建 agent
    # 所有必要的默认值（系统提示、上下文处理）均已内置
    agent = create_agent(
        base_url="https://api.example.com",          # 你的 API 端点
        api_key="your-api-key",                       # 你的 API key
        model="gpt-3.5-turbo",                        # 模型名称
        model_config={                                 # 可选模型参数
            "temperature": 0.7,
            "stream": True,                            # 启用流式输出
        }
    )
    logger.info("✅ Agent 创建成功。")

    print("💬 开始示例对话：")
    print()

    # 示例 1：第一次交互
    user_input = "你好！能告诉我 AmritaCore 是什么吗？"

    print(f"👤 用户：{user_input}")

    # 为这次用户输入获取一个 chat object
    chat = agent.get_chatobject(user_input)

    print("🤖 助手：", end="")

    # 逐 token 流式输出响应
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            # message 可以是字符串或 Message 对象
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")
        await chat  # 等待任务完成后再退出

    print("\n")  # 响应后换行

    # 示例 2：追问 — agent 自动保持上下文
    follow_up = "能解释一下它的主要特性吗？"

    print(f"👤 用户：{follow_up}")

    # 只需用同一个 agent 创建另一个 chat object
    chat2 = agent.get_chatobject(follow_up)

    print("🤖 助手：", end="")

    async with chat2.begin():
        async for message in chat2.io_stream.get_response_generator():
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")
        await chat2  # 等待任务完成后再退出

    print("\n")  # 响应后换行

    print("🎉 基础示例成功完成！")
    print("-" * 50)
    print("💡 演示的关键概念：")
    print("   • 使用 create_agent() 创建 agent")
    print("   • 通过 agent.get_chatobject() 获取 chat object")
    print("   • 流式响应")
    print("   • 多轮对话自动上下文保持")
    print("   • 内置默认系统提示")


async def minimal_example():
    """
    最小示例：展示运行 AmritaCore 的必要步骤。
    """
    print("\n🧪 最小示例")
    print("-" * 30)

    # 在创建 agent 之前初始化 AmritaCore
    await minimal_init()
    # 仅用必要参数创建 agent
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-4",
        model_config={"temperature": 0.7}
    )

    # 获取 chat object 并获取完整响应（非流式）
    chat = agent.get_chatobject("你好！你能做什么？")

    async with chat.begin():
        response = await chat.full_response()
        await chat  # 等待任务完成后再退出

    print(f"💬 响应：{response}")
    print("✅ 最小示例完成！")


if __name__ == "__main__":
    # 通过正确的初始化运行示例
    asyncio.run(basic_example())
    asyncio.run(minimal_example())

    print("\n✨ 所有示例完成！")
```

## 配置详情

新 API 简化了配置：

- **Agent 创建**：`create_agent(base_url, api_key, model, model_config)` 是唯一入口。它在内部设置默认系统提示、上下文管理和模型预设。
- **模型配置**：通过 `model_config` 字典传递任意模型参数（如 `temperature`、`stream`）。`stream` 标志控制响应是否流式输出。
- **上下文处理**：agent 自动保持对话历史。你**不需要**手动管理 `MemoryModel` 或 `train` 消息——它们已内置，除非你需要导出或反序列化记忆。
- **系统提示**：提供合理的默认系统提示。如需自定义，`create_agent` 接受可选的 `train` 参数。

## 常见问题排查

**问题**：API 端点连接错误  
**解决**：验证 `base_url` 和 `api_key` 是否正确，网络是否能到达该端点。

**问题**：长对话中 Token 用量过高  
**解决**：agent 自动应用记忆抽象（如果后端启用）来摘要旧消息。你也可以调整 `LLM_Config` 中的 `max_tokens` 参数来限制响应长度。

**问题**：响应缓慢  
**解决**：检查网络延迟。如需更快响应，可考虑使用更小的模型或降低 `temperature`（可能使输出更确定性，略快一些）。流式输出（`stream=True`）也能让你更早开始显示文本。

**问题**：对话上下文似乎丢失  
**解决**：确保在同一轮对话的所有回合中使用**同一个 agent 实例**。每次 `agent.get_chatobject()` 调用会自动使用 agent 的内部上下文。
