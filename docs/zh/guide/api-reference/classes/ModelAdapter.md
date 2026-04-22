# ModelAdapter

`ModelAdapter` 是一个 dataclass，作为 AmritaCore 中模型协议适配器的基类。

## 概述

`ModelAdapter` 类提供了一个统一的接口，用于将不同的 AI 模型提供商（如 OpenAI、Anthropic 等）集成到 AmritaCore 框架中。适配器负责与外部 API 通信、处理响应，并将其转换为框架可以使用的标准化格式。

除非标记为抽象或明确禁用注册，否则适配器在定义时会自动注册到 [`AdapterManager`](#adaptermanager)。

## 类定义

```python
from dataclasses import dataclass, field
from amrita_core.protocol import ModelAdapter
from amrita_core.types import ModelPreset
from amrita_core.config import AmritaConfig

@dataclass
class ModelAdapter:
    preset: ModelPreset
    config: AmritaConfig = field(default_factory=get_config)
    __override__: bool = False
```

## 属性

### `preset`

- **类型**: [`ModelPreset`](ModelPreset.md)
- **描述**: 模型预设配置，包含模型名称、API 密钥、基础 URL 和其他设置。

### `config`

- **类型**: [`AmritaConfig`](AmritaConfig.md)
- **描述**: 适配器的全局配置，包括超时设置、重试策略和令牌限制。
- **默认值**: 从 `get_config()` 函数获取。

### `__override__`

- **类型**: `bool`
- **描述**: 是否允许覆盖具有相同协议的已注册适配器。设置为 `True` 以替换已注册的适配器。
- **默认值**: `False`

## 方法

### get_adapter_protocol() _(抽象方法)_

获取此适配器的协议标识符。

这是一个必须由所有具体适配器子类实现的抽象静态方法。它返回此适配器支持的协议名称。

**返回值**: `str | tuple[str, ...]` - 单个协议字符串或多个协议字符串的元组。

**示例**:

```python
class MyAdapter(ModelAdapter):
    @staticmethod
    def get_adapter_protocol() -> str:
        return "my-custom-protocol"

# 或支持多个协议
class MultiProtocolAdapter(ModelAdapter):
    @staticmethod
    def get_adapter_protocol() -> tuple[str, str]:
        return ("openai", "azure-openai")
```

### get_type()

获取指示适配器主要功能的适配器类型。

**返回值**: `ADAPTER_TYPE | tuple[ADAPTER_TYPE, ...]` - 适配器类型，可以是：

- `"text-gen"`: 文本生成/补全（默认）
- `"embed"`: 嵌入向量生成
- `"rerank"`: 重排序（计划中）

**默认值**: `"text-gen"`

**示例**:

```python
class EmbeddingAdapter(ModelAdapter):
    @staticmethod
    def get_type() -> str:
        return "embed"
```

### call_api()

调用模型 API 生成文本补全。

此方法应被重写以实现文本生成的实际 API 调用逻辑。它在响应到达时生成响应块，支持流式和非流式模式。

**参数**:

- `messages` (`Iterable`): 发送到模型的消息列表
- `**kwargs`: 额外的关键字参数

**返回值**: `AsyncGenerator[COMPLETION_RETURNING, None]` - 异步生成器，生成：

- `str`: 文本块（流式模式下）
- [`MessageContent`](../protocol.md#messagecontent): 自定义消息内容对象
- [`UniResponse`](UniResponse.md): 包含完整内容和使用信息的最终响应

**异常**: `NotImplementedError` - 如果子类未实现

**示例**:

```python
async def call_api(self, messages: Iterable, **kwargs):
    # 实现您的 API 调用逻辑
    async for chunk in self._stream_response(messages):
        yield chunk

    # 生成最终响应
    yield UniResponse(content=full_response, usage=usage_info)
```

### call_tools()

使用模型的函数调用功能执行工具调用。

此方法向模型发送带有可用工具的消息，并检索模型的工具调用决策。

**参数**:

- `messages` (`Iterable`): 发送到模型的消息列表
- `tools` (`list[ToolFunctionSchema]`): 可用工具模式列表
- `tool_choice` ([`ToolChoice`](../models.md#toolchoice) | `None`, 可选): 模型应如何选择工具。默认为 `None`（自动选择）。

**返回值**: [`UniResponse`](UniResponse.md)`[None, list[`[ToolCall`](ToolCall.md)`] | None]` - 包含模型工具调用决策的响应。

**异常**: `NotImplementedError` - 如果子类未实现

**示例**:

```python
async def call_tools(self, messages, tools, tool_choice=None):
    # 使用工具调用模型
    response = await self.client.chat.completions.create(
        model=self.preset.model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice or "auto"
    )

    # 提取工具调用
    tool_calls = [
        ToolCall.model_validate(tc)
        for tc in response.choices[0].message.tool_calls
    ]

    return UniResponse(tool_calls=tool_calls, content=None)
```

### call_embed()

为输入文本生成嵌入向量。

嵌入适配器应重写此方法以实现嵌入生成逻辑。

**参数**:

- `texts` (`Iterable[str]`): 要生成嵌入的文本列表
- `**kwargs`: 额外的关键字参数

**返回值**: `Sequence[EmbeddingChunk]` - 嵌入块序列，每个包含嵌入向量及其原始索引。

**异常**: `NotImplementedError` - 如果子类未实现

**示例**:

```python
async def call_embed(self, texts: Iterable[str], **kwargs):
    embeddings = []
    for idx, text in enumerate(texts):
        # 生成嵌入向量
        vector = await self._generate_embedding(text)
        embeddings.append(
            EmbeddingChunk(embedding=vector, index=idx)
        )
    return embeddings
```

### protocol _(属性)_

获取模型协议适配器标识符。

**返回值**: `str | tuple[str, ...]` - 来自 `get_adapter_protocol()` 的协议标识符。

## 自动注册

适配器在定义时会向 [`AdapterManager`](#adaptermanager) 自动注册，除非：

1. 类具有 `__abstract__ = True` 属性
2. 类具有 `__no_register__ = True` 属性

**示例**:

```python
# 此适配器将自动注册
class MyAdapter(ModelAdapter):
    @staticmethod
    def get_adapter_protocol() -> str:
        return "my-protocol"

# 此适配器不会自动注册
class AbstractBaseAdapter(ModelAdapter):
    __abstract__ = True

    @staticmethod
    def get_adapter_protocol() -> str:
        return "abstract"
```

## 内置适配器

AmritaCore 提供了几个内置适配器：

### OpenAIAdapter

- **协议**: `"openai"`, `"__main__"`
- **位置**: `amrita_core.builtins.adapter.OpenAIAdapter`
- **特性**:
  - 支持流式和非流式模式
  - 通过 OpenAI 的函数调用 API 实现工具调用
  - 兼容任何 OpenAI 兼容的 API 端点

### AnthropicAdapter

- **协议**: `"anthropic"`, `"claude"`
- **位置**: `amrita_core.builtins.adapter.AnthropicAdapter`
- **特性**:
  - 支持流式响应
  - 目前为实验性（工具调用尚未实现）
  - 针对 Claude 模型优化

## 创建自定义适配器

创建自定义适配器的步骤：

1. 继承 `ModelAdapter`
2. 实现 `get_adapter_protocol()`（必需）
3. 重写 `call_api()` 用于文本生成
4. 可选重写 `call_tools()` 用于工具调用
5. 可选重写 `call_embed()` 用于嵌入生成
6. 如果不是文本生成适配器，可选重写 `get_type()`

**完整示例**:

```python
from collections.abc import AsyncGenerator, Iterable
from amrita_core.protocol import ModelAdapter, COMPLETION_RETURNING
from amrita_core.types import ModelPreset, UniResponse, UniResponseUsage

class CustomAdapter(ModelAdapter):
    """自定义模型适配器示例"""

    @staticmethod
    def get_adapter_protocol() -> str:
        return "custom-api"

    async def call_api(
        self,
        messages: Iterable,
        **kwargs
    ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
        # 您的自定义 API 逻辑
        response_text = ""

        # 处理消息并调用您的 API
        async for chunk in self._fetch_chunks(messages):
            response_text += chunk
            yield chunk

        # 返回最终响应
        yield UniResponse(
            content=response_text,
            usage=UniResponseUsage(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150
            )
        )
```

## 相关组件

- [`AdapterManager`](#adaptermanager): 管理适配器注册和检索
- [`ModelPreset`](ModelPreset.md): 适配器的配置预设
- [`AmritaConfig`](AmritaConfig.md): 适配器使用的全局配置
- [`UniResponse`](UniResponse.md): 标准化响应格式
- [`EmbeddingChunk`](EmbeddingChunk.md): 嵌入结果结构
- [`ToolCall`](ToolCall.md): 工具调用表示
- [`OpenAIAdapter`](#内置适配器): 内置 OpenAI 适配器实现
- [`AnthropicAdapter`](#内置适配器): 内置 Anthropic 适配器实现

## AdapterManager

`AdapterManager` 类管理模型适配器的注册和检索。

### 方法

#### get_adapters()

获取所有已注册的适配器。

**返回值**: `dict[str, type[ModelAdapter]]` - 将协议名称映射到适配器类的字典。

#### safe_get_adapter(protocol)

安全地按协议名称获取适配器。

**参数**:

- `protocol` (`str`): 协议标识符

**返回值**: `type[ModelAdapter] | None` - 如果找到则返回适配器类，否则返回 `None`。

#### get_adapter(protocol)

按协议名称获取适配器。

**参数**:

- `protocol` (`str`): 协议标识符

**返回值**: `type[ModelAdapter]` - 适配器类。

**异常**: `ValueError` - 如果未找到给定协议的适配器。

#### register_adapter(adapter)

注册适配器类。

**参数**:

- `adapter` (`type[ModelAdapter]`): 要注册的适配器类。

**异常**:

- `ValueError` - 如果具有相同协议的适配器已注册且 `__override__` 为 `False`。
- `TypeError` - 如果协议不是字符串或字符串元组。
