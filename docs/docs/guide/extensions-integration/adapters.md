# Model Adapters

Adapters normalize provider-specific APIs into one interface
(`ModelAdapter` in `amrita_core.base.adapter`). `create_agent()` picks the
adapter from your `protocol` argument.

## Built-in Adapters

### OpenAIAdapter

**Protocols**: `"openai"`, `"deepseek"`, `"azure"`, or any OpenAI-compatible
endpoint.

```python
agent = create_agent(
    base_url="https://api.deepseek.com",     # OpenAI-compatible
    api_key=os.environ["DEEPSEEK_API_KEY"],
    model="deepseek-chat",
)
```

**Provider-specific request tracing**: the adapter reads request ids from
`x-request-id` (OpenAI), `x-ds-trace-id` / `eo-log-uuid` (DeepSeek) — the id
surfaces on empty-response warnings so you can trace a failed call in provider
logs.

### AnthropicAdapter

**Protocols**: `"anthropic"`, `"claude"`.

```python
agent = create_agent(
    protocol="anthropic",
    base_url="https://api.anthropic.com",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    model="claude-sonnet-4-5",
)
```

Supports tool calling and **extended thinking** (`ThinkingConfig`), including
thinking-delta streaming and signature round-tripping.

> If the `anthropic` SDK is missing, the adapter logs an info and skips
> registration — no import errors.

## Thinking Mode and `reasoning_content`

Thinking-capable models (DeepSeek thinking, Claude extended thinking) return
reasoning alongside the answer. AmritaCore stores it in
`Message.reasoning_content` and **passes it back verbatim** on subsequent
requests — required by DeepSeek (HTTP 400 otherwise) and by Claude's signature
round-trip. The thinking filter (`thinking_config.content_mode`) strips it for
the _request payload_ without mutating the live message objects.

## Writing a Custom Adapter

Subclass `ModelAdapter`; it **registers itself automatically**
(`__init_subclass__` → `AdapterManager().register_adapter(cls)`):

```python
from amrita_core.base.adapter import ModelAdapter

class MyAdapter(ModelAdapter):
    # Declare which protocol(s) this adapter serves.
    @staticmethod
    def get_adapter_protocol() -> str | tuple[str, ...]:
        return "my-provider"

    async def call_api(self, messages, **kwargs):
        # Streaming: yield UniResponse chunks (content / reasoning / usage).
        ...

    async def call_tools(self, messages, tools, tool_choice=None, **kwargs):
        # Tool-calling completion; return UniResponse[None, list[ToolCall] | None].
        ...

    async def call_embed(self, texts, **kwargs):
        # Embeddings; return Sequence[EmbeddingChunk].
        ...
```

Then use it — no explicit registration call needed:

```python
agent = create_agent(
    protocol="my-provider",
    base_url="https://my-provider.example.com",
    api_key=...,
    model="my-model",
)
```

Set `__override__ = True` on the class to replace an already-registered
adapter for the same protocol.

**Contract checklist**:

- Streaming: yield `UniResponse` chunks (content / reasoning / usage)
- Return `reasoning_content` on assistant messages for thinking providers
- Expose `metadata.original_request_id` when the provider sends a trace id
