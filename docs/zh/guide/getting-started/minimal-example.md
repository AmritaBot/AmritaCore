# 最小示例

## 2.2.1 5分钟快速入门

这是一个最小示例，帮助您开始使用 AmritaCore：

```python
import asyncio
from amrita_core import ChatObject, init, load_amrita
from amrita_core.config import AmritaConfig
from amrita_core.preset import PresetManager
from amrita_core.types import MemoryModel, Message, ModelConfig, ModelPreset

async def minimal_example():
    # 初始化 AmritaCore
    init()

    # 设置最小配置
    from amrita_core.config import set_config
    set_config(AmritaConfig())

    # 加载 AmritaCore 组件
    await load_amrita()

    # 创建模型预设
    preset = ModelPreset(
        model="gpt-3.5-turbo",
        base_url="YOUR_API_ENDPOINT",  # 替换为您的 API 端点
        api_key="YOUR_API_KEY",        # 替换为您的 API 密钥
        config=ModelConfig(stream=True)
    )

    # 注册模型预设
    preset_manager = PresetManager()
    preset_manager.add_preset(preset)
    preset_manager.set_default_preset(preset.name)

    # 创建上下文和系统消息
    context = MemoryModel()
    train = Message(content="您是一个有用的助手。", role="system")

    # 创建并运行聊天交互
    chat = ChatObject(
        context=context,
        session_id="minimal_session",
        user_input="你好，你能做什么？",
        train=train.model_dump(),
    )

    async with chat.begin():
        print(await chat.full_response())

# 运行示例
if __name__ == "__main__":
    asyncio.run(minimal_example())
```

## 2.2.2 代码示例说明

在这个最小示例中：

1. 我们使用 `init()` 初始化 AmritaCore，它准备内部组件
2. 我们使用 `AmritaConfig()` 设置最小配置
3. 我们使用 `load_amrita()` 加载核心组件
4. 我们创建一个模型预设，定义要使用哪个 LLM
5. 我们使用 PresetManager 注册预设
6. 我们创建记忆上下文和系统消息
7. 我们使用参数实例化 ChatObject
8. 我们调用 `chat.begin()` 来执行交互
9. 我们使用 `await chat.full_response()` 获取最终的完整响应
10. 最后，我们获取完整响应

## 2.2.3 运行和调试

要运行示例：

1. 安装 AmritaCore
2. 将 `YOUR_API_ENDPOINT` 和 `YOUR_API_KEY` 替换为实际值
3. 使用 `python your_script.py` 执行脚本

要进行调试，您可以通过在代码中配置日志记录器来启用详细日志。
