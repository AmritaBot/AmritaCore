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

## 3.2.5 PresetManager 预设管理（推荐实践）

**推荐使用 [PresetManager](../api-reference/classes/PresetManager.md) 来管理您所有的预设。** PresetManager 提供集中管理、验证和自动 fallback 机制。

### 为什么使用 PresetManager？

1. **集中管理**: 所有预设存储在一个地方
2. **自动 Fallback**: 如果未选择预设，自动使用默认预设
3. **验证**: 防止重复名称并验证配置
4. **测试**: 内置测试功能以验证预设功能
5. **单例模式**: 确保整个应用程序中的状态一致

### 基本用法

```python
from amrita_core.preset import PresetManager
from amrita_core.types import ModelPreset, ModelConfig

# 初始化管理器（单例）
manager = PresetManager()

# 添加预设
manager.add_preset(ModelPreset(
    model="gpt-3.5-turbo",
    name="fast",
    api_key="sk-xxx",
    config=ModelConfig(stream=True)
))

manager.add_preset(ModelPreset(
    model="gpt-4",
    name="smart",
    api_key="sk-xxx"
))

# 设置默认预设（可选但推荐）
manager.set_default_preset("fast")

# 获取预设 - 如果未指定将自动 fallback 到默认值
preset = manager.get_preset("smart")  # 特定预设
default = manager.get_default_preset()  # 默认预设（自动 fallback）
```

### 自动 Fallback 行为

当您调用 `get_default_preset()` 但未设置默认值时：

- 如果通过 `set_default_preset()` 设置了默认值，返回该预设
- 如果**未设置默认值**，从可用预设中自动随机选择一个预设
- 这确保您的应用程序永远不会因为缺少预设配置而失败

```python
manager = PresetManager()
manager.add_preset(preset1)
manager.add_preset(preset2)

# 未设置默认值 - 将自动 fallback 到随机预设
default = manager.get_default_preset()  # 返回 preset1 或 preset2
```

完整的 API 参考请见 [PresetManager](../api-reference/classes/PresetManager.md)。

## 3.2.6 TextContent 文本内容

[TextContent](../api-reference/classes/TextContent.md) 类表示消息中的文本内容：

```python
from amrita_core.types import TextContent

# 创建文本内容
content = TextContent(text="这是实际的消息文本")
```

## 3.2.7 UniResponse 统一响应

[UniResponse](../api-reference/classes/UniResponse.md) 类为响应提供统一格式：

```python
from amrita_core.types import UniResponse

# 处理统一响应
response = UniResponse(content="响应内容", usage=...)
```

## 3.2.8 对话状态管理

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

## 3.2.9 会话隔离

此处请见[安全控制](../security-mechanisms.md)第6.3章。

## 3.2.10 嵌入向量支持

AmritaCore通过适配器系统提供内置的嵌入向量生成功能。

### 适配器类型

AmritaCore适配器通过 `ADAPTER_TYPE` 字面量类型别名（定义为 `Literal["text-gen", "embed"]`）支持多种类型：

- **`"text-gen"`**: 传统的文本生成/完成（默认）
- **`"embed"`**: 嵌入向量生成
- **`"rerank"`**: 重排序功能（计划在未来版本中实现）

### 嵌入适配器实现

要创建嵌入适配器，需要继承 [`ModelAdapter`](../api-reference/classes/ModelAdapter.md) 并实现所需方法：

```python
from collections.abc import Iterable, Sequence
from amrita_core.protocol import ModelAdapter
from amrita_core.types import EmbeddingChunk, ModelPreset

class MyEmbeddingAdapter(ModelAdapter):
    @staticmethod
    def get_adapter_protocol() -> str:
        return "my-embedding-protocol"

    @staticmethod
    def get_type() -> str:
        return "embed"

    async def call_embed(self, texts: Iterable[str], **kwargs) -> Sequence[EmbeddingChunk]:
        """为给定文本生成嵌入向量"""
        embeddings = []
        for idx, text in enumerate(texts):
            # 您的嵌入逻辑在这里
            embedding_vector = self._generate_embedding(text)
            embeddings.append(
                EmbeddingChunk(embedding=embedding_vector, index=idx)
            )
        return embeddings

    def _generate_embedding(self, text: str) -> list[float]:
        # 实现您的嵌入生成逻辑
        pass
```

**注意**：

- `get_adapter_protocol()` 是必须实现的抽象方法，返回适配器协议名称
- `get_type()` 返回适配器类型，默认为 `"text-gen"`，嵌入适配器应返回 `"embed"`
- `call_embed()` 方法接收文本列表，返回 [`EmbeddingChunk`](../api-reference/classes/EmbeddingChunk.md) 序列

### 使用嵌入适配器

嵌入适配器可以通过标准预设系统使用：

```python
from amrita_core.preset import PresetManager, ModelPreset
from amrita_core.libchat import call_completion

# 为嵌入适配器创建预设
preset = ModelPreset(
    protocol="my-embedding-protocol",
    model="embedding-model-v1",
    # ... 其他配置
)

# 注册预设
PresetManager().register_preset("embedding-preset", preset)

# 使用嵌入适配器
texts = ["Hello world", "How are you?"]
embeddings = await call_completion(preset=preset, messages=texts)
```

**注意**：`call_completion` 函数会自动检测适配器类型并调用适当的方法（`"text-gen"` 调用 `call_api`，`"embed"` 调用 `call_embed`）。

### EmbeddingChunk 结构

[`EmbeddingChunk`](../api-reference/classes/EmbeddingChunk.md) 类表示单个嵌入结果：

```python
from amrita_core.types import EmbeddingChunk

# EmbeddingChunk 包含两个字段：
# - embedding: Sequence[float] - 作为浮点数序列的嵌入向量
# - index: int - 文本在输入序列中的原始索引
```

此结构保持与OpenAI嵌入响应格式的兼容性，同时提供类型安全性。

### 类型安全和验证

AmritaCore包含适配器使用的自动类型验证：

```python
# 如果适配器不支持 "text-gen"，这将引发 RuntimeError
response = await call_completion(preset=text_gen_preset, messages=["Hello"])

# 这将与嵌入适配器正常工作
embeddings = await call_completion(preset=embedding_preset, messages=["Hello"])
```

框架验证适配器类型是否与预期用途匹配，防止意外误用嵌入适配器进行文本生成，反之亦然。
