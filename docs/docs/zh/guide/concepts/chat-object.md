# ChatObject — 对话对象

[ChatObject](../api-reference/classes/ChatObject.md) 是管理单个对话的核心类。与智能体的每一次交互——聊天、工具调用、多轮交流——都通过 `ChatObject` 实例进行。

虽然[教程](../tutorials/index.md)展示了使用 `create_agent()` 工厂函数创建智能体的推荐方式，但本页解释 `ChatObject` 是什么，以及各个部分如何协同工作。

## 什么是 ChatObject？

一个 `ChatObject` 捆绑了单次对话所需的一切：

- **输入**：`train`（系统消息）和 `user_input`（用户查询）
- **状态**：将对话记忆绑定到会话的 `session_id`
- **能力**：从[数据后端](data-backend.md)加载的工具、MCP 客户端和预设
- **I/O**：产出响应的 `io_stream`，支持可选的流式回调

```python
import asyncio
from amrita_core import ChatObject
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

backend = BackendSlots(ability=LegacyBackend(), memory=LegacyBackend())

chat = ChatObject(
    train={"role": "system", "content": "你是一个有帮助的助手。"},
    user_input="你好！",
    context=None,
    session_id="session_123",
    backend=backend,
)

async def msg_getter(chatobj: ChatObject) -> None:
    async for message in chatobj.io_stream.get_response_generator():
        print(message if isinstance(message, str) else message.get_content(), end="")
    print("\n")

async with chat.begin():
    await msg_getter(chat)
    await chat  # 等待任务完成再退出
```

## PresetManager — 预设管理器

[PresetManager](../api-reference/classes/PresetManager.md) 管理模型预设：

```python
from amrita_core.preset import PresetManager, ModelPreset

preset_manager = PresetManager()

# 添加预设
preset = ModelPreset(...)
preset_manager.add_preset(preset)
preset_manager.set_default_preset(preset.name)

# 获取可用预设
presets = preset_manager.get_presets()
```

## 流处理设计

AmritaCore 对所有响应使用流式处理，以提供实时反馈：

```python
# 响应以异步生成器形式返回
async for chunk in chat.io_stream.get_response_generator():
    # 实时处理每个块
    print(chunk, end="")
```

## 基于回调的响应

AmritaCore 支持基于回调的响应：

```python
async def callback(chunk):
    print(chunk, end="")

chat.io_stream.set_callback_func(callback)
chat.begin()
await chat
```

## 记忆摘要机制

记忆摘要机制自动压缩对话历史以管理 token 使用：

```python
# 通过 LLMConfig 配置
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # 在达到 token 限制时摘要部分对话
)
```

## 挂起与恢复

AmritaCore 提供了一个内置的**挂起/恢复机制**，允许你在处理过程中随时暂停和恢复 `ChatObject` 的执行流。此功能支持交互式应用程序，其中用户干预或外部事件可能需要临时暂停智能体的工作流。

主要特性包括：

- 非阻塞挂起，不会阻塞主事件循环
- 对执行流的细粒度控制
- 支持超时以防止无限等待
- 与所有智能体策略无缝集成

详细使用示例和高级场景请参见[挂起与恢复机制](../advanced/suspend.md)文档。
