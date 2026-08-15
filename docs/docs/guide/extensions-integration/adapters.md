# Model Adapters

Adapters normalize provider-specific APIs into one interface
(`ModelAdapter` in `amrita_core.base.adapter`).

> **Adapter + Provider**: the connection is decided jointly by the **adapter**
> (which _protocol_ — the wire format — is spoken) and the **provider** (which
> _endpoint and model_ — `base_url` + `model` — is reached). An adapter is not
> vendor-specific: the same OpenAI-compatible adapter serves OpenAI, DeepSeek,
> Azure, or any local server; only `base_url`/`model` change.

## Built-in Adapters

### OpenAIAdapter

Serves any OpenAI-compatible endpoint. Registered protocols: `"openai"`,
`"__main__"` (the default `ModelPreset` protocol).

```python
agent = create_agent(
    base_url="https://api.deepseek.com",  # any OpenAI-compatible endpoint
    api_key=os.environ["API_KEY"],
    model="deepseek-chat",
)
```

`create_agent()` always builds a preset with the default protocol
(`"__main__"` → OpenAIAdapter), so an OpenAI-compatible endpoint works with
zero protocol configuration — DeepSeek, Azure and friends are not separate
protocols, just different `base_url`/`model` values.

**Provider-specific request tracing**: the adapter reads request ids from
`x-request-id` (OpenAI), `x-ds-trace-id` / `eo-log-uuid` (DeepSeek) — the id
surfaces on empty-response warnings so you can trace a failed call in provider
logs.

### AnthropicAdapter

Registered protocols: `"anthropic"`, `"claude"`.

`create_agent()` has no `protocol` parameter — to select a non-default
adapter, build a `ModelPreset` with the desired `protocol` and pass it to
`AgentRuntime`:

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

Set `__override__ = True` on the class to replace an already-registered
adapter for the same protocol.

**Contract checklist**:

- Streaming: yield `UniResponse` chunks (content / reasoning / usage)
- Return `reasoning_content` on assistant messages for thinking providers
- Expose `metadata.original_request_id` when the provider sends a trace id
