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

`create_agent()` 总是构造默认协议（`"__main__"` -> OpenAIAdapter）的 preset，
所以 OpenAI 兼容端点零协议配置即可使用——DeepSeek、Azure 等**不是**独立
协议，只是不同的 `base_url`/`model` 取值。

**供应商专属请求追踪**：适配器从 `x-request-id`（OpenAI）、
`x-ds-trace-id` / `eo-log-uuid`（DeepSeek）读取请求 id——空响应警告会带上
该 id，方便你在供应商日志中定位失败调用。

### OpenAIResponsesAdapter

说 OpenAI **Responses** API（`/v1/responses`）。注册协议：`"openai-responses"`。

```python
preset = ModelPreset(
    name="responses",
    protocol="openai-responses",
    base_url="https://api.openai.com/v1",
    api_key=os.environ["OPENAI_API_KEY"],
    model="gpt-5",
    config=ModelConfig(),
)
```

与 Chat Completions 有两处线上格式不同，这也是它存在的理由：

- 工具返回是一条 `function_call_output`，其 `output` 可以是
  `input_text` / `input_image` / `input_file` 组成的列表，因此该适配器声明
  `tool_result_multimodal=True`——截图以图片形态送到模型，而不是占位符；
- 工具调用是独立的 `function_call` 条目，不再挂在 assistant 消息的字段上；
  文本以 `output_text` 块返回。

该适配器是**无状态**的：每次请求都把完整对话放在 `input` 里，`store` 固定为
`False`，从不使用 `previous_response_id`。续接对话不依赖服务端任何状态，因此
重试、preset 回退或进程重启的行为完全一致。

reasoning item 会被回传：一轮产生推理时，适配器把 item 的 id 与加密内容存进
`reasoning_signature`，下次请求原样带回——Responses API 对有工具调用的后续请求
有此要求。

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

思考是否开启由供应商默认决定：字段缺省表示「沿用默认」，因此关闭必须显式传值。
设置 `ThinkingConfig(thinking_type="disabled")` 后，适配器会发送
`thinking: {"type": "disabled"}`（Chat Completions、Anthropic）或
`reasoning: {"effort": "none"}`（Responses）。

## 编写自定义适配器

继承 `ModelAdapter`；它会**自动注册**（`__init_subclass__` ->
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

## 列出模型

`fetch_models(preset)` 是适配器上的类方法，模型选择器不用构造实例就能直接问端点：

```python
models = await OpenAIAdapter.fetch_models(preset)
for model in models:
    print(model.id, model.name, model.context_window, model.input_modalities)
```

`OpenAIAdapter` 与 `OpenAIResponsesAdapter` 读 `GET /models`；
`AnthropicAdapter` 读 `GET /v1/models`。能力声明在 `features.fetch_models`，
调用前先看它——兼容端点未必实现了该路由，失败会以 `AdapterRequestError` 抛出。

## 异常

适配器方法不会把 SDK 异常原样漏出去。所有失败都以
`amrita_core.exceptions.AdapterError` 或其子类抛出：

| 类型                       | 含义                             |
| -------------------------- | -------------------------------- |
| `AdapterAuthError`         | 凭据缺失、无效或权限不足         |
| `AdapterRateLimitError`    | 被供应商限流                     |
| `AdapterTimeoutError`      | 超过 `llm_timeout`               |
| `AdapterConnectionError`   | 连不上供应商（DNS、TLS、socket） |
| `AdapterRequestError`      | 供应商拒收请求（4xx/5xx）        |
| `AdapterResponseError`     | 响应无法解析                     |
| `UnsupportedContentError`  | 载荷含该协议无法承载的内容块     |

原始 SDK 异常保留在 `.original`，HTTP 状态码在 `.status_code`，消息前缀带适配器名。
第三方适配器给方法加上 `normalize_adapter_errors("<名字>")` 就能获得同样行为，
协程与异步生成器都支持。

`UnsupportedContentError` 在请求发出**之前**抛出，也不会被当成传输失败重试，
详见[工具返回](../concepts/tool.md#并非每个适配器都能携带每种块)。
