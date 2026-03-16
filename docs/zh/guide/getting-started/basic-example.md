# 基础示例

## 2.3.1 完整的基础功能演示

让我们来看一个更完整的示例，展示上下文保留和多次交互：

```python
"""
AmritaCore 基础示例 - 核心功能的简单演示。

此示例演示如何初始化 AmritaCore、配置它，
并运行与 AI 助手的基本聊天会话。
"""

import asyncio

from amrita_core import ChatObject, init, load_amrita, logger
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig
from amrita_core.preset import PresetManager
from amrita_core.types import MemoryModel, Message, ModelConfig, ModelPreset


async def basic_example():
    """
    基础示例，演示 AmritaCore 的核心功能。
    展示初始化、配置和简单聊天交互。
    """
    print("🚀 启动 AmritaCore 基础示例")
    print("-" * 50)

    # 配置 AmritaCore
    # FunctionConfig 定义Agent的一般行为
    func = FunctionConfig(
        use_minimal_context=False,  # 使用完整上下文或最小上下文
    )

    # LLMConfig 定义语言模型行为
    llm = LLMConfig(
        enable_memory_abstract=True,  # 启用记忆摘要功能
    )

    # 将配置合并为主配置
    config = AmritaConfig(
        function_config=func,
        llm=llm,
    )

    # 应用配置
    from amrita_core.config import set_config

    set_config(config)

    # 加载 AmritaCore 组件
    await load_amrita()

    # 设置模型预设 - 定义要使用的 LLM
    preset = ModelPreset(
        model="gpt-3.5-turbo",  # 模型名称
        base_url="INSERT_YOUR_API_ENDPOINT_HERE",  # API 端点
        api_key="INSERT_YOUR_API_KEY_HERE",  # API 密钥
        config=ModelConfig(stream=True),  # 启用流式响应
    )

    # 注册模型预设
    preset_manager = PresetManager()
    preset_manager.add_preset(preset)
    preset_manager.set_default_preset(preset.name)
    logger.info("✅ 注册模型预设。")

    # 创建记忆上下文以保存对话历史
    context = MemoryModel()

    # 定义系统指令（AI 应该如何行为）
    train = Message(
        content="您是一个有用的 AI 助手。请简洁准确地回答。",
        role="system",
    )

    print("💬 开始示例对话:")
    print()

    # 示例 1: 简单文本交互
    user_input = "你好！你能告诉我 AmritaCore 是什么吗？"

    print(f"👤 用户: {user_input}")

    # 创建用于交互的 ChatObject
    chat = ChatObject(
        context=context,
        session_id="basic_example_session",
        user_input=user_input,
        train=train.model_dump(),  # 将 Message 转换为字典
    )

    # 处理响应并显示
    print("🤖 助手: ", end="")

    async with chat.begin():
        async for message in chat.get_response_generator():
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")

    print("\n")  # 响应后换行

    # 使用最新的对话状态更新上下文
    context = chat.data

    # 示例 2: 后续问题以演示上下文保留
    follow_up = "你能解释它的主要功能吗？"

    print(f"👤 用户: {follow_up}")

    # 使用更新的上下文创建另一个 ChatObject
    chat2 = ChatObject(
        context=context,
        session_id="basic_example_session",
        user_input=follow_up,
        train=train.model_dump(),
    )

    print("🤖 助手: ", end="")

    # 处理后续问题
    await chat2.begin()

    async for message in chat2.get_response_generator():
        content = message if isinstance(message, str) else message.get_content()
        print(content, end="")

    print("\n")  # 响应后换行

    print("🎉 基础示例成功完成！")
    print("-" * 50)
    print("💡 演示的关键概念:")
    print("   • 初始化和配置")
    print("   • 创建 ChatObject 实例")
    print("   • 流式响应")
    print("   • 上下文管理")
    print("   • 会话处理")


async def minimal_example():
    """
    最小示例，显示运行 AmritaCore 的基本步骤。
    """
    print("\n🧪 最小示例")
    print("-" * 30)

    # 最小配置
    from amrita_core.config import set_config

    set_config(AmritaConfig())

    # 加载 AmritaCore
    await load_amrita()

    # 注意: 在实际场景中，您将在此处配置模型预设
    print("✅ AmritaCore 已使用最小配置加载")

    # 创建上下文和系统消息
    context = MemoryModel()
    train = Message(content="您是一个有用的助手。", role="system")

    # 创建并运行聊天交互
    chat = ChatObject(
        context=context,
        session_id="minimal_session",
        user_input="你能做什么？",
        train=train.model_dump(),
    )


    # 收集响应（仅显示其工作）
    async with chat.begin():
        response = await chat.full_response()
    print(f"💬 响应长度: {len(response)} 个字符")
    print("✅ 最小示例完成！")


if __name__ == "__main__":
    # 初始化 AmritaCore
    init()

    # 运行示例
    asyncio.run(basic_example())
    asyncio.run(minimal_example())

    print("\n✨ 所有示例已完成！")

```

## 2.3.2 配置详情

该示例展示了几个重要的配置选项：

- `use_minimal_context=False`: 使用完整对话历史而不是仅最后一条消息
- `enable_memory_abstract=True`: 启用自动上下文摘要以管理Token使用

## 2.3.3 常见问题排查

**问题**: API 端点连接错误
**解决方案**: 验证您的 API 端点和密钥是否正确，以及网络连接是否正常。

**问题**: 高Token使用率
**解决方案**: 启用记忆摘要 (`enable_memory_abstract=True`) 并考虑在简单查询时使用最小上下文模式。

**问题**: 响应缓慢
**解决方案**: 检查您的网络连接和 API 提供商性能。考虑使用较小的模型以获得更快的响应。
