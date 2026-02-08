# 数据类型和对话管理

## 3.2.1 Message 消息类型

[Message](../api-reference/classes/Message.md) 类表示对话中的单条消息：

```python
from amrita_core.types import Message

# 创建系统消息
system_msg = Message(content="您是一个有用的助手。", role="system")

# 创建用户消息
user_msg = Message(content="您好，您好吗？", role="user")

# 创建助手消息
assistant_msg = Message(content="我很好，谢谢！", role="assistant")
```

## 3.2.2 MemoryModel 记忆模型

[MemoryModel](../api-reference/classes/MemoryModel.md) 类存储对话历史和上下文：

```python
from amrita_core.types import MemoryModel

# 创建新记忆上下文
memory = MemoryModel()

# 将消息添加到记忆
memory.messages.append(system_msg)
memory.messages.append(user_msg)
memory.messages.append(assistant_msg)
```

## 3.2.3 ModelConfig 模型配置

[ModelConfig](../api-reference/classes/ModelConfig.md) 类保存模型特定设置：

```python
from amrita_core.types import ModelConfig

# 配置流式传输和其他模型选项
model_config = ModelConfig(stream=True)
```

## 3.2.4 ModelPreset 模型预设

[ModelPreset](../api-reference/classes/ModelPreset.md) 类为特定模型定义完整配置：

```python
from amrita_core.types import ModelPreset

# 定义模型预设
preset = ModelPreset(
    model="gpt-3.5-turbo",
    base_url="https://api.openai.com/v1",
    api_key="your-api-key",
    config=ModelConfig(stream=True)
)
```

## 3.2.5 TextContent 文本内容

[TextContent](../api-reference/classes/TextContent.md) 类表示消息中的文本内容：

```python
from amrita_core.types import TextContent

# 创建文本内容
content = TextContent(text="这是实际的消息文本")
```

## 3.2.6 UniResponse 统一响应

[UniResponse](../api-reference/classes/UniResponse.md) 类为响应提供统一格式：

```python
from amrita_core.types import UniResponse

# 处理统一响应
response = UniResponse(content="响应内容", usage=...)
```

## 3.2.7 对话状态管理

对话状态通过 MemoryModel 和 ChatObject 类管理：

```python
# 创建新的对话上下文
context = MemoryModel()

# 添加初始系统消息
train = Message(content="您是一个有用的助手。", role="system")

# 创建用于交互的 ChatObject
chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="你好！",
    train=train.model_dump()
)

# 处理交互
await chat.begin()

# 使用新状态更新上下文
updated_context = chat.data
```