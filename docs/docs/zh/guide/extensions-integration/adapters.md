# 模型适配器

适配器把供应商专属 API 规范化为统一接口（`amrita_core.base.adapter` 中的
`ModelAdapter`）。`create_agent()` 根据你的 `protocol` 参数选择适配器。

## 内置适配器

### OpenAIAdapter

**协议**：`"openai"`、`"deepseek"`、`"azure"` 或任意 OpenAI 兼容端点。

```python
agent = create_agent(
    base_url="https://api.deepseek.com",     # OpenAI 兼容
    api_key=os.environ["DEEPSEEK_API_KEY"],
    model="deepseek-chat",
)
```

**供应商专属请求追踪**：适配器从 `x-request-id`（OpenAI）、
`x-ds-trace-id` / `eo-log-uuid`（DeepSeek）读取请求 id——空响应警告会带上
该 id，方便你在供应商日志中定位失败调用。

### AnthropicAdapter

**协议**：`"anthropic"`、`"claude"`。

```python
agent = create_agent(
    protocol="anthropic",
    base_url="https://api.anthropic.com",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    model="claude-sonnet-4-5",
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
agent = create_agent(
    protocol="my-provider",
    base_url="https://my-provider.example.com",
    api_key=...,
    model="my-model",
)
```

在类上设 `__override__ = True` 可替换同协议已注册的适配器。

**契约清单**：

- 流式：产出 `UniResponse` chunk（content / reasoning / usage）
- 对 thinking 供应商在 assistant 消息上返回 `reasoning_content`
- 供应商发送追踪 id 时暴露 `metadata.original_request_id`
