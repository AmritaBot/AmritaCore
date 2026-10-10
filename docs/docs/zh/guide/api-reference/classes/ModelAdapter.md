# ModelAdapter

`ModelAdapter` 是一个数据类，作为 AmritaCore 中模型协议适配器的基类。

## 概述

`ModelAdapter` 类提供了统一的接口，用于将不同的 AI 模型提供商（如 OpenAI、Anthropic 等）集成到 AmritaCore 框架中。适配器负责与外部 API 通信、处理响应，并将其转换为框架可用的标准化格式。

适配器在定义时会自动注册到 [`AdapterManager`](#adaptermanager)，除非被标记为抽象或显式禁用注册。

> **注意**：`ModelAdapter` 基类已从 `amrita_core.protocol` 迁移至 `amrita_core.base.adapter`。`amrita_core.protocol` 兼容入口已在 v0.10.x+ 移除；请从 `amrita_core.base.adapter` 导入。

## 类定义

```python
from dataclasses import dataclass, field
from amrita_core.base.adapter import ModelAdapter
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

- **类型**：[`ModelPreset`](ModelPreset.md)
- **描述**：包含模型名称、API 密钥、基础 URL 和其他设置的模型预设配置。

### `config`

- **类型**：[`AmritaConfig`](AmritaConfig.md)
- **描述**：适配器的全局配置，包括超时设置、重试策略和 token 限制。
- **默认**：来自 `get_config()` 函数。

### `__override__`

- **类型**：`bool`
- **描述**：是否允许用相同协议覆盖已有适配器。设为 `True` 可替换已注册的适配器。
- **默认**：`False`

### `supports_agentic_call`

- **类型**：`bool`
- **描述**：该适配器是否实现了 [`agentic_call_api()`](#agentic_call_api)。声明为 `ClassVar`，因此它是类上的能力标记，而不是每个实例上的 dataclass 字段。能在一次请求里同时流出文本与工具调用的适配器应设为 `True`。
- **默认**：`False`

### `supports_agentic_call`

- **类型**：`bool`
- **描述**：该适配器是否实现了 [`agentic_call_api()`](#agentic_call_api)。声明为 `ClassVar`，因此它是类上的能力标记，而不是每个实例上的 dataclass 字段。能在一次请求里同时流出文本与工具调用的适配器应设为 `True`。
- **默认**：`False`

## 方法

### get*adapter_protocol() *(抽象)\_

获取此适配器的协议标识符。

这是一个抽象静态方法，所有具体的适配器子类都**必须**实现它。它返回此适配器支持的协议名称。

**返回**：`str | tuple[str, ...]` - 单个协议字符串，或多个协议字符串组成的元组。

**示例**：

```python
class MyAdapter(ModelAdapter):
    @staticmethod
    def get_adapter_protocol() -> str:
        return "my-custom-protocol"


# Or support multiple protocols
class MultiProtocolAdapter(ModelAdapter):
    @staticmethod
    def get_adapter_protocol() -> tuple[str, str]:
        return ("openai", "azure-openai")
```

### get_type()

获取适配器类型，表示其主要功能。

**返回**：`ADAPTER_TYPE | tuple[ADAPTER_TYPE, ...]` - 适配器类型，可以是：

- `"text-gen"`：文本生成/补全（默认）
- `"embed"`：嵌入向量生成
- `"rerank"`：重排序（计划于未来支持）

**默认**：`"text-gen"`

**示例**：

```python
class EmbeddingAdapter(ModelAdapter):
    @staticmethod
    def get_type() -> str:
        return "embed"
```

### call_api()

调用模型 API 生成文本补全。

应覆写此方法以实现文本生成的实际 API 调用逻辑。它会在响应块到达时逐个产出，同时支持流式和非流式模式。

**参数**：

- `messages` (`Iterable`)：要发送给模型的消息列表
- `**kwargs`：其他关键字参数

**返回**：`AsyncGenerator[COMPLETION_RETURNING, None]` - 产出以下内容的异步生成器：

- `str`：文本块（流式模式下）
- `MessageContent`：自定义消息内容对象
- `UniResponse`：包含完整内容和用量信息的最终响应

**抛出**：`NotImplementedError` - 若子类未实现

**示例**：

```python
async def call_api(self, messages: Iterable, **kwargs):
    # Implement your API call logic
    async for chunk in self._stream_response(messages):
        yield chunk

    # Yield final response
    yield UniResponse(content=full_response, usage=usage_info)
```

### agentic_call_api()

 __mcp_status=0; printf 
__MCP_CMD_4a563f8c__%d
 0 2>/dev/null || __MCP_CMD_4a563f8c__0 echo

[`call_api()`](#call_api) 只流式输出文本，[`call_tools()`](#call_tools) 返回工具调用但不流式，两者都无法驱动一个既要实时显示输出、又要继续接受下一轮工具调用的 agent 循环。本方法在一次请求里同时做到：文本分片边到边发，末尾的 `UniResponse` 携带聚合完成的 `tool_calls`。`tool_calls` 为空表示模型直接给出了终答，而不是又要发起一轮工具调用。

/root/AmritaCore/**可选能力**。基类实现直接抛 `NotImplementedError`，调用方会回退到传统的 `call_api()` + `call_tools()` 组合。实现它的适配器必须同时把 `supports_agentic_call` 置为 `True`。

**参数**：

- `messages` (`Iterable`)：发送给模型的消息列表
- `tools` (`list[ToolFunctionSchema] | None`)：要暴露的工具定义；`None` 或空表示纯文本轮次
- `tool_choice` (`ToolChoice | None`)：provider 如何选择工具
- `**kwargs`：透传给 provider 的额外关键字参数

**返回**：`AsyncGenerator[COMPLETION_RETURNING, None]` —— 与 [`call_api()`](#call_api) 形态一致，只是末尾的 `UniResponse` 可能同时携带 `tool_calls`。

**抛出**：`NotImplementedError` —— 适配器未实现时

**示例**：

```python
final = None
async for chunk in adapter.agentic_call_api(messages, tools=tools, tool_choice="auto"):
    if isinstance(chunk, UniResponse):
        final = chunk
    else:
        print(chunk, end="")

if final.tool_calls:
    ...  # 再跑一轮工具
```

> **注意**：流式模式下工具调用的参数是分片到达的。内置适配器按 `index` 聚合，每次调用只产出一个完整的 `ToolCall`，调用方不会看到半成品。

### agentic_call_api()

一次调用同时拿到流式文本与结构化工具调用。

[`call_api()`](#call_api) 只流式输出文本，[`call_tools()`](#call_tools) 返回工具调用但不流式，两者都无法驱动一个既要实时显示输出、又要继续接受下一轮工具调用的 agent 循环。本方法在一次请求里同时做到：文本分片边到边发，末尾的 `UniResponse` 携带聚合完成的 `tool_calls`。`tool_calls` 为空表示模型直接给出了终答，而不是又要发起一轮工具调用。

这是**可选能力**。基类实现直接抛 `NotImplementedError`，调用方会回退到传统的 `call_api()` + `call_tools()` 组合。实现它的适配器必须同时把 `supports_agentic_call` 置为 `True`。

**参数**：

- `messages` (`Iterable`)：发送给模型的消息列表
- `tools` (`list[ToolFunctionSchema] | None`)：要暴露的工具定义；`None` 或空表示纯文本轮次
- `tool_choice` (`ToolChoice | None`)：provider 如何选择工具
- `**kwargs`：透传给 provider 的额外关键字参数

**返回**：`AsyncGenerator[COMPLETION_RETURNING, None]` —— 与 [`call_api()`](#call_api) 形态一致，只是末尾的 `UniResponse` 可能同时携带 `tool_calls`。

**抛出**：`NotImplementedError` —— 适配器未实现时

**示例**：

```python
final = None
async for chunk in adapter.agentic_call_api(messages, tools=tools, tool_choice="auto"):
    if isinstance(chunk, UniResponse):
        final = chunk
    else:
        print(chunk, end="")

if final.tool_calls:
    ...  # 再跑一轮工具
```

> **注意**：流式模式下工具调用的参数是分片到达的。内置适配器按 `index` 聚合，每次调用只产出一个完整的 `ToolCall`，调用方不会看到半成品。

### call_tools()

利用模型的函数调用能力执行工具调用。

此方法将消息连同可用工具一起发送给模型，并获取模型的工具调用决策。

**参数**：

- `messages` (`Iterable`)：要发送给模型的消息列表
- `tools` (`list[ToolFunctionSchema]`)：可用工具 schema 列表
- `tool_choice` (`ToolChoice` | `None`，可选)：模型应如何选择工具。默认 `None`（自动选择）。

**返回**：`UniResponse[None, list[ToolCall] | None]` - 包含模型工具调用决策的响应。

**抛出**：`NotImplementedError` - 若子类未实现

**示例**：

```python
async def call_tools(self, messages, tools, tool_choice=None):
    # Call model with tools
    response = await self.client.chat.completions.create(
        model=self.preset.model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice or "auto",
    )

    # Extract tool calls
    tool_calls = [
        ToolCall.model_validate(tc) for tc in response.choices[0].message.tool_calls
    ]

    return UniResponse(tool_calls=tool_calls, content=None)
```

### call_embed()

为输入文本生成嵌入向量。

嵌入适配器应覆写此方法以实现嵌入生成逻辑。

**参数**：

- `texts` (`Iterable[str]`)：要为其生成嵌入的文本列表
- `**kwargs`：其他关键字参数

**返回**：`Sequence[EmbeddingChunk]` - 嵌入块序列，每个块包含一个嵌入向量及其原始索引。

**抛出**：`NotImplementedError` - 若子类未实现

**示例**：

```python
async def call_embed(self, texts: Iterable[str], **kwargs):
    embeddings = []
    for idx, text in enumerate(texts):
        # Generate embedding vector
        vector = await self._generate_embedding(text)
        embeddings.append(EmbeddingChunk(embedding=vector, index=idx))
    return embeddings
```

### protocol _(属性)_

获取模型协议适配器标识符。

**返回**：`str | tuple[str, ...]` - 来自 `get_adapter_protocol()` 的协议标识符。

## 自动注册

适配器在类定义时会自动注册到 [`AdapterManager`](#adaptermanager)，除非：

1. 类具有 `__abstract__ = True` 属性
2. 类具有 `__no_register__ = True` 属性

**示例**：

```python
# This adapter will be automatically registered
class MyAdapter(ModelAdapter):
    @staticmethod
    def get_adapter_protocol() -> str:
        return "my-protocol"


# This adapter will NOT be automatically registered
class AbstractBaseAdapter(ModelAdapter):
    __abstract__ = True

    @staticmethod
    def get_adapter_protocol() -> str:
        return "abstract"
```

## 内置适配器

AmritaCore 提供了若干内置适配器：

### OpenAIAdapter

- **协议**：`"openai"`、`"__main__"`
- **位置**：`amrita_core.builtins.adapter.OpenAIAdapter`
- **特性**：
  - 同时支持流式和非流式模式
  - 通过 OpenAI 的函数调用 API 实现工具调用
  - 兼容任何 OpenAI 兼容的 API 端点

### AnthropicAdapter

- **协议**：`"anthropic"`、`"claude"`
- **位置**：`amrita_core.builtins.adapter.AnthropicAdapter`
- **特性**：
  - 支持流式响应
  - 通过 Anthropic 的工具使用 API 提供完整的工具调用支持
  - 针对 Claude 模型优化，正确处理消息格式

## 编写自定义适配器

编写自定义适配器：

1. 继承 `ModelAdapter`
2. 实现 `get_adapter_protocol()`（必需）
3. 覆写 `call_api()` 以实现文本生成
4. 可选：覆写 `call_tools()` 以实现工具调用
5. 可选：覆写 `call_embed()` 以实现嵌入生成
6. 可选：若非文本生成适配器，覆写 `get_type()`

**完整示例**：

```python
from collections.abc import AsyncGenerator, Iterable
from amrita_core.base.adapter import ModelAdapter, COMPLETION_RETURNING
from amrita_core.types import ModelPreset, UniResponse, UniResponseUsage


class CustomAdapter(ModelAdapter):
    """Custom model adapter example"""

    @staticmethod
    def get_adapter_protocol() -> str:
        return "custom-api"

    async def call_api(
        self, messages: Iterable, **kwargs
    ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
        # Your custom API logic here
        response_text = ""

        # Process messages and call your API
        async for chunk in self._fetch_chunks(messages):
            response_text += chunk
            yield chunk

        # Return final response
        yield UniResponse(
            content=response_text,
            usage=UniResponseUsage(
                prompt_tokens=100, completion_tokens=50, total_tokens=150
            ),
        )
```

## 相关组件

- [`AdapterManager`](#adaptermanager)：管理适配器的注册与获取
- [`ModelPreset`](ModelPreset.md)：适配器的配置预设
- [`AmritaConfig`](AmritaConfig.md)：适配器使用的全局配置
- `UniResponse`：标准化响应格式
- [`EmbeddingChunk`](EmbeddingChunk.md)：嵌入结果结构
- `ToolCall`：工具调用表示
- [`OpenAIAdapter`](#built-in-adapters)：内置 OpenAI 适配器实现
- [`AnthropicAdapter`](#built-in-adapters)：内置 Anthropic 适配器实现

## AdapterManager

`AdapterManager` 类管理模型适配器的注册与获取。

### 方法

#### get_adapters()

获取所有已注册的适配器。

**返回**：`dict[str, type[ModelAdapter]]` - 协议名到适配器类的字典映射。

#### safe_get_adapter(protocol)

按协议名安全地获取适配器。

**参数**：

- `protocol` (`str`)：协议标识符

**返回**：`type[ModelAdapter] | None` - 找到则返回适配器类，否则返回 `None`。

#### get_adapter(protocol)

按协议名获取适配器。

**参数**：

- `protocol` (`str`)：协议标识符

**返回**：`type[ModelAdapter]` - 适配器类。

**抛出**：`ValueError` - 若给定协议找不到适配器。

#### register_adapter(adapter)

注册适配器类。

**参数**：

- `adapter` (`type[ModelAdapter]`)：要注册的适配器类。

**抛出**：

- `ValueError` - 若已注册相同协议的适配器且 `__override__` 为 `False`。
- `TypeError` - 若协议不是字符串或字符串元组。
