# 模型适配器

适配器把供应商专属 API 规范化为统一接口（`amrita_core.base.adapter` 中的
`ModelAdapter`）。

> **适配器 + 供应商**：连接由**适配器**（说哪种*协议*、即线上格式）与**供应商**
> （连到哪个*端点和模型*、即 `base_url` + `model`）共同决定。适配器并非厂商
> 特化：同一个 OpenAI 兼容适配器同时服务 OpenAI、DeepSeek、Azure 或任意
> 本地服务——只需改 `base_url`/`model`。

## 内置适配器

### OpenAIAdapter

服务任意 OpenAI 兼容端点。注册协议：`"openai"`、`"__main__"`（`ModelPreset`
的默认协议）。

```python
agent = create_agent(
    base_url="https://api.deepseek.com",  # 任意 OpenAI 兼容端点
    api_key=os.environ["API_KEY"],
    model="deepseek-chat",
)
```

`create_agent()` 总是构造默认协议（`"__main__"` → OpenAIAdapter）的 preset，
所以 OpenAI 兼容端点零协议配置即可使用——DeepSeek、Azure 等**不是**独立
协议，只是不同的 `base_url`/`model` 取值。

**供应商专属请求追踪**：适配器从 `x-request-id`（OpenAI）、
`x-ds-trace-id` / `eo-log-uuid`（DeepSeek）读取请求 id——空响应警告会带上
该 id，方便你在供应商日志中定位失败调用。

### AnthropicAdapter

注册协议：`"anthropic"`、`"claude"`。

`create_agent()` **没有** `protocol` 参数——要选择非默认适配器，需构造带
目标 `protocol` 的 `ModelPreset` 并传给 `AgentRuntime`：

```python
from amrita_core.agent.functions import AgentRuntime
from amrita_core.config import AmritaConfig
from amrita_core.types import Message, ModelConfig, ModelPreset

preset = ModelPreset(
    name="anthropic-default",
    protocol="anthropic",
    base_url="https://api.anthropic.com",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    model="claude-sonnet-4-5",
    config=ModelConfig(),
)
agent = AgentRuntime(
    config=AmritaConfig(),
    preset=preset,
    train=Message(content="You are a helpful assistant.", role="system"),
)
```

支持工具调用与**扩展思考**（`ThinkingConfig`），包括思考增量流式与签名
往返。

> 缺少 `anthropic` SDK 时，适配器记录 info 并跳过注册——不会导入报错。

## Thinking 模式与 `reasoning_content`

支持思考的模型（DeepSeek thinking、Claude extended thinking）在答案之外
返回推理。AmritaCore 把它存在 `Message.reasoning_content` 中，并在后续请求
**原样回传**——DeepSeek 要求如此（否则 HTTP 400），Claude 需要签名往返。
思考过滤器（`thinking_config.content_mode`）只为*请求负载*剥离它，
不改动活动消息对象。

## 编写自定义适配器

继承 `ModelAdapter`；它会**自动注册**（`__init_subclass__` →
`AdapterManager().register_adapter(cls)`）：

```python
from amrita_core.base.adapter import ModelAdapter


class MyAdapter(ModelAdapter):
    # 声明此适配器服务的协议。
    @staticmethod
    def get_adapter_protocol() -> str | tuple[str, ...]:
        return "my-provider"

    async def call_api(self, messages, **kwargs):
        # 流式：产出 UniResponse chunk（content / reasoning / usage）。
        ...

    async def call_tools(self, messages, tools, tool_choice=None, **kwargs):
        # 工具调用完成；返回 UniResponse[None, list[ToolCall] | None]。
        ...

    async def call_embed(self, texts, **kwargs):
        # 嵌入；返回 Sequence[EmbeddingChunk]。
        ...
```

然后直接使用——无需显式注册调用：

```python
from amrita_core.agent.functions import AgentRuntime
from amrita_core.config import AmritaConfig
from amrita_core.types import Message, ModelConfig, ModelPreset

preset = ModelPreset(
    name="my-provider-default",
    protocol="my-provider",
    base_url="https://my-provider.example.com",
    api_key=...,
    model="my-model",
    config=ModelConfig(),
)
agent = AgentRuntime(
    config=AmritaConfig(),
    preset=preset,
    train=Message(content="You are a helpful assistant.", role="system"),
)
```

在类上设 `__override__ = True` 可替换同协议已注册的适配器。

**契约清单**：

- 流式：产出 `UniResponse` chunk（content / reasoning / usage）
- 对 thinking 供应商在 assistant 消息上返回 `reasoning_content`
- 供应商发送追踪 id 时暴露 `metadata.original_request_id`
