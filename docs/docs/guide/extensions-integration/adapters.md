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
(`"__main__"` -> OpenAIAdapter), so an OpenAI-compatible endpoint works with
zero protocol configuration — DeepSeek, Azure and friends are not separate
protocols, just different `base_url`/`model` values.

**Provider-specific request tracing**: the adapter reads request ids from
`x-request-id` (OpenAI), `x-ds-trace-id` / `eo-log-uuid` (DeepSeek) — the id
surfaces on empty-response warnings so you can trace a failed call in provider
logs.

### OpenAIResponsesAdapter

Speaks the OpenAI **Responses** API (`/v1/responses`). Registered protocol:
`"openai-responses"`.

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

Two wire shapes differ from Chat Completions, and they are why this adapter
exists:

- a tool result is a `function_call_output` item whose `output` may be a list of
  `input_text` / `input_image` / `input_file` parts, so the adapter declares
  `tool_result_multimodal=True` — a screenshot reaches the model as an image
  instead of a placeholder;
- tool calls are separate `function_call` items rather than fields on an
  assistant message, and text comes back as `output_text` parts.

The adapter is **stateless**: each request sends the whole conversation as
`input`, `store` is pinned to `False`, and `previous_response_id` is never used.
Nothing server-side is needed to continue a conversation, so a retry, a preset
fallback or a process restart all behave the same way.

Reasoning items are replayed. When a turn produces reasoning, the adapter keeps
the items' ids and encrypted content on `reasoning_signature` and sends them back
on the next request, which the Responses API requires for tool-calling
follow-ups.

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

Thinking is provider-defaulted: an absent field means "keep the default", so
turning it off requires an explicit value. `ThinkingConfig(thinking_type="disabled")`
makes the adapters send `thinking: {"type": "disabled"}` (Chat Completions,
Anthropic) or `reasoning: {"effort": "none"}` (Responses).

## Writing a Custom Adapter

Subclass `ModelAdapter`; it **registers itself automatically**
(`__init_subclass__` -> `AdapterManager().register_adapter(cls)`):

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

## Listing Models

`fetch_models(preset)` is a class method on every adapter, so a model picker can
ask the endpoint directly without building an instance:

```python
models = await OpenAIAdapter.fetch_models(preset)
for model in models:
    print(model.id, model.name, model.context_window, model.input_modalities)
```

`OpenAIAdapter` and `OpenAIResponsesAdapter` read `GET /models`;
`AnthropicAdapter` reads `GET /v1/models`. The capability is declared as
`features.fetch_models` — check it before calling, since a compatible endpoint
may not implement the route; that failure surfaces as `AdapterRequestError`.

## Errors

Adapter methods never leak an SDK exception. Every failure is raised as
`amrita_core.exceptions.AdapterError`, or a subclass that names the cause:

| Type                    | Meaning                                             |
| ----------------------- | --------------------------------------------------- |
| `AdapterAuthError`      | credentials missing, invalid or lacking permission  |
| `AdapterRateLimitError` | provider throttled the request                      |
| `AdapterTimeoutError`   | request exceeded `llm_timeout`                      |
| `AdapterConnectionError`| provider unreachable (DNS, TLS, socket)             |
| `AdapterRequestError`   | provider rejected the request (4xx/5xx)             |
| `AdapterResponseError`  | response the adapter cannot interpret               |
| `UnsupportedContentError` | payload carries blocks this protocol cannot hold  |

The untouched SDK exception stays reachable on `.original`, the HTTP status on
`.status_code`, and the message is prefixed with the adapter name. Third-party
adapters can get the same behaviour by decorating their methods with
`normalize_adapter_errors("<name>")`; it handles coroutines and async generators.

`UnsupportedContentError` is raised **before** a request is sent and is never
retried as a transport failure — see [tool results](../concepts/tool.md#not-every-adapter-can-carry-every-block).
