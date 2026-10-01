# Migration Guide: 0.13 → 1.0

AmritaCore 1.0 removes the local tokenizer and moves context management onto the
model's own attention window. This page lists every breaking change and what to
use instead.

## At a Glance

| Removed / renamed                                                 | Replacement                                                    |
| ----------------------------------------------------------------- | -------------------------------------------------------------- |
| `amrita_core.tokenizer` module                                    | provider-reported usage (`MemoryModel.usage`)                  |
| `TokenizerManager`, `BaseTokenizer`                               | (none — tokenization is the provider's job)                    |
| `get_tokens()`, `hybrid_token_count()`                            | `UniResponseUsage` from the provider response                  |
| `FunctionConfig.no_tokenizer`                                     | (none)                                                         |
| `FunctionConfig.tokenizer_used`                                   | (none)                                                         |
| `LLMConfig.tokens_count_mode`                                     | (none)                                                         |
| `LLMConfig.enable_tokens_limit`                                   | (none)                                                         |
| `config.llm.max_tokens` for requests                              | `resolve_max_output(preset, config)`                           |
| `LLMConfig.enable_memory_abstract`                                | `LLMConfig.enable_compaction`                                  |
| `LLMConfig.memory_abstract_proportion`                            | `LLMConfig.compaction_trigger_ratio`                           |
| `LLMConfig.memory_abstract_threshold`                             | `LLMConfig.compaction_trigger_ratio` (+ `memory_length_limit`) |
| `chatmanager.MemoryLimiter`                                       | `ContextCompactor` + `NORMALIZE_MESSAGES`                      |
| `UsageRegistry` and friends                                       | `SessionUsageProxy`                                            |
| `ChatObject(context=...)`                                         | `ChatObject(session_id=...)` (now required)                    |
| `chat.state` / `StateContext`                                     | `chat.session_id`, `chat.data`, DI contexts                    |
| `LegacyBackend(ctx=...)`                                          | `LegacyBackend()`                                              |
| `HybridReActAgentStrategy`                                        | `ReActAgentStrategy`                                           |
| `BuiltinName`                                                     | (none)                                                         |
| Tool arguments left unchecked                                     | `function_config.validate_tool_arguments` (default `True`)     |
| `SuspendEnum.MEMORY_APPEND`, `.FINALIZE`, `.CALL_SINGLE_STRATEGY` | (none — never emitted)                                         |
| `BuiltinAgentConfig.agent_tool_call_notice`                       | (none — filter the stream)                                     |
| `BuiltinAgentConfig.agent_reasoning_hide`                         | (none — filter the stream)                                     |

## 1. The Tokenizer Is Gone

AmritaCore no longer ships a tokenizer, and `jieba` is no longer an extra. Token
accounting now comes from the number the provider already returns with each
response:

```python
# before
from amrita_core import get_tokens

tokens = get_tokens(messages)

# after
tokens = chat.data.usage  # UniResponseUsage | None, from the last request
```

Every completion the provider answers reports usage back into
`MemoryModel.usage`, so no local counting is needed. If your provider does not
report usage, see the message-count fallback in [section 3](#3-compaction-replaces-memory-abstraction).

## 2. The Attention Window Lives on the Preset

`max_context` (input budget) and `max_output` (response reservation) are now
`ModelPreset` fields. `LLMConfig.session_tokens_windows` and `LLMConfig.max_tokens`
are only the fallbacks used when a preset leaves them unset.

```python
# before: one global number for every model
config.llm.session_tokens_windows = 128_000
config.llm.max_tokens = 4_000

# after: the model declares its own window
preset = ModelPreset(
    model="deepseek-chat",
    name="deepseek",
    api_key="sk-...",
    max_context=64_000,
    max_output=8_000,
)
```

Two helpers resolve a preset field against the config so callers never branch on
`None`:

```python
from amrita_core.types.preset import resolve_max_context, resolve_max_output

window = resolve_max_context(preset, config)
budget = resolve_max_output(preset, config)
```

If you were passing `config.llm.max_tokens` into a provider request, use
`resolve_max_output(preset, config)` instead. The built-in adapters already do.

### New Defaults

`max_output` now defaults to `28000` and `LLMConfig.max_tokens` to `10000`. The
old global default of `1000` was small enough that a reasoning model could spend
the entire budget on thinking and return an empty answer, and a compaction
summary could come back empty and silently skip the fold.

`max_tokens` is now only the last resort — it is reached when a preset sets
`max_output=None` explicitly, so a model that needs a different ceiling declares
it on its own preset.

## 3. Compaction Replaces Memory Abstraction

`enable_memory_abstract` is now `enable_compaction`. The proportion/threshold
pair is replaced by a ratio of the model's window, plus a message-count
fallback:

```python
# before
config.llm.enable_memory_abstract = True
config.llm.memory_abstract_proportion = 0.5
config.llm.memory_abstract_threshold = 4000

# after
config.llm.enable_compaction = True
config.llm.compaction_trigger_ratio = 0.9  # fraction of the attention window
config.llm.memory_length_limit = 200  # message-count fallback, 0 = off
config.llm.enable_overflow_recovery = True  # compact and retry on overflow
```

The threshold is no longer a number you maintain by hand: `ContextCompactor`
derives it from `max_context` × `compaction_trigger_ratio`, so it follows the
model. Compaction fires on whichever comes first:

- the prompt size the provider reported for the previous request reaches the
  threshold
- history reaches `memory_length_limit` messages

The second trigger exists because the first one needs the provider to report
usage. Leave `memory_length_limit` at its default unless every provider you use
reports usage.

The summary is stored on `MemoryModel.abstract` and rendered back into the
system instruction by the train template, so it never enters the message list.

### `MemoryLimiter` Is Gone

`chatmanager.MemoryLimiter` was removed. Its three responsibilities now live
elsewhere:

| Responsibility                         | Now handled by                                       |
| -------------------------------------- | ---------------------------------------------------- |
| Cap the message count                  | `LLMConfig.memory_length_limit` (dual trigger)       |
| Flatten content blocks for text models | `NORMALIZE_MESSAGES` node (`llm.enable_multi_modal`) |
| Fold long history                      | `ContextCompactor` / `COMPACT` node                  |

Note that `LLMConfig.enable_multi_modal` is now consumed by `NORMALIZE_MESSAGES`
instead: with it off, block-list bodies are flattened to text before the request
is built.

## 4. Billing Is a First-Class Concern

New public types:

- `RateConfig` — unit-price snapshot, attached to a `ModelPreset`
- `BillingRecord` — one provider request's usage plus the pricing that applied
- `BillingBackend` / `NullBillingBackend` — an optional external sink
- `BackendSlots.billing` — the slot that carries it

```python
from decimal import Decimal

from amrita_core import ModelPreset, RateConfig

preset = ModelPreset(
    model="deepseek-chat",
    name="deepseek",
    api_key="sk-...",
    rate=RateConfig(per=1_000_000, input=Decimal("0.27"), output=Decimal("1.10")),
)
```

Records accumulate on `MemoryModel.billing`, which is the default persistence
path — a billing backend is only needed to mirror them into an external cost
store. `SessionUsageProxy` replaces the old `UsageRegistry` family and is
created per run by `ChatObject`.

AmritaCore does not compute currency amounts; it stores the rate and the token
counts so consumers can derive cost themselves. See
[BillingBackend](api-reference/classes/BillingBackend.md) for the
`DatabackendOptions.skip_billing_commit` switch.

## 5. `StateContext` Is Gone

`StateContext` was deprecated since 0.10 and is now removed.

```python
# before
from amrita_core import StateContext

ctx = StateContext(session_id="s1")
chat = ChatObject(train=train, user_input="hi", context=ctx)
sid = chat.state.session_id

# after
chat = ChatObject(train=train, user_input="hi", session_id="s1")
sid = chat.session_id
```

- `ChatObject(context=...)` is gone. `session_id` is now **required**:
  constructing a `ChatObject` without one raises
  `ValueError("session_id must be provided")`
- `chat.state` (getter and setter) is gone
- `LegacyBackend(ctx=...)` is gone; `LegacyBackend()` takes no arguments

Replacements for what the accessor exposed:

| Old                         | New                                  |
| --------------------------- | ------------------------------------ |
| `chat.state.session_id`     | `chat.session_id`                    |
| `chat.state.memory`         | `chat.data` (a `MemoryModel`)        |
| `chat.state.ability`        | `chat._di_ability.ability`           |
| `chat.state` (whole object) | read the individual `_di_*` contexts |

## 6. `HybridReActAgentStrategy` Is Gone

The deprecated `HybridReActAgentStrategy` (XML-rendering, `agent-mixed`) was
removed. Use `ReActAgentStrategy`, which pairs tool calls with their results
using the OpenAI-compatible `assistant(tool_calls)` + `tool` message structure.

```python
# before
from amrita_core.builtins.agent import HybridReActAgentStrategy

# after
from amrita_core.builtins.agent import ReActAgentStrategy
```

The `HYBRID_TEMPLATE` constant went with it. The `agent-mixed` **category** is
unaffected: it is `ReActAgentStrategy.get_category()`, and it is what makes the
workflow dispatch a strategy into the agent loop (see
[Agent Strategy](concepts/agent-strategy.md)).

## 7. Serialization Needs `mode="json"`

`RateConfig.input` / `.output` are `Decimal`. `model_dump()` therefore returns
`Decimal` objects, which `json.dump` cannot serialize:

```python
# before
json.dump(memory.model_dump(), f)

# after
json.dump(memory.model_dump(mode="json"), f)
```

`ModelPreset.save()` already does this. Apply the same change anywhere you
persist a `MemoryModel` or `ModelPreset` yourself.

## 8. Tool Arguments Are Validated

`call_tool()` now checks the arguments the model produced against the tool's
parameter schema before running the handler. A violation raises
`ValidationError`, which the agent loop returns to the model as an `ERR: ...`
tool result.

Most tools need no change, but two behaviours are worth knowing:

- A tool that used to receive malformed arguments now receives an error result
  instead. If your handler deliberately tolerated bad input, either validate
  inside it or turn the check off with
  `FunctionConfig(validate_tool_arguments=False)`.
- Omitted arguments stay omitted, so a Python default on the handler still
  applies.

The same layer adds the projection direction, so a tool can be described by a
Pydantic model instead of a hand-written schema:

```python
from pydantic import BaseModel, Field

from amrita_core.tools.manager import on_tools
from amrita_core.tools.schema import function_definition_from_pydantic


class LookupArgs(BaseModel):
    """Look a user up by id."""

    user_id: int = Field(description="Numeric user id", ge=1)


@on_tools(function_definition_from_pydantic(LookupArgs, name="lookup"))
async def lookup(args: dict) -> str:
    return f"user {args['user_id']}"
```

`simple_tool`'s type-hint parser moved to `amrita_core.tools.schema` as
`python_type_to_property_schema` / `pydantic_model_to_property_schema`. The
private `_python_type_to_property_schema` name it used to carry is gone.

MCP tools also stopped losing their constraints: `minimum`, `maximum`,
`pattern`, `minLength`, `maxLength`, `multipleOf`, `exclusiveMinimum`,
`exclusiveMaximum`, `const`, `default` and `additionalProperties` are now
carried through from the server's JSON Schema.

## 9. Three Unused `SuspendEnum` Values Are Gone

`SuspendEnum.MEMORY_APPEND`, `SuspendEnum.FINALIZE` and
`SuspendEnum.CALL_SINGLE_STRATEGY` were declared but never attached to a node,
so nothing ever emitted them. They are removed.

The practical consequence is only for code that **waited** on them:

```python
# before — would block forever, nothing ever emitted this tag
await chat.io_stream.wait_to_suspend(SuspendEnum.FINALIZE.value)
```

If you need a hook at the end of a run, use the `COMPLETION` event
([Event System](concepts/event.md)) or the `COMMIT_MEMORY` tag, which is
attached to a real node. Note that `MEMORY_APPEND` was never the tag on
`APPEND_RESPONSE` — that node carries `SuspendEnum.MEMORY`, alongside `COMPACT`.

## 10. `hide` Switches Are Gone — Filter the Stream

`BuiltinAgentConfig.agent_tool_call_notice` and `agent_reasoning_hide` are
removed. They tried to decide inside the framework what a consumer should see,
and they disagreed with each other: the "calling" notice ignored
`agent_tool_call_notice` entirely, so `"hide"` never hid anything.

The framework now always emits structured events and leaves presentation to the
consumer:

| Event             | `type`            | `extra_type` |
| ----------------- | ----------------- | ------------ |
| Tool call starts  | `function_call`   | —            |
| Tool call returns | `function_call`   | —            |
| Reasoning stream  | `reasoning_chunk` | `cot_chunk`  |

```python
# before
config.builtin.agent_tool_call_notice = "hide"

# after — drop what you do not want to show
async for msg in chat.io_stream.get_response_generator():
    if getattr(msg, "metadata", {}).get("type") == "function_call":
        continue
```

`agent_reasoning_hide` was never read anywhere in the framework, so removing it
changes nothing at runtime.

## 11. `full_response()` Returns the Answer Only

`ChatObject.full_response()` used to concatenate every item in the stream,
including `MessageWithMetadata` events. Because a reasoning model streams its
thinking as `reasoning_chunk` events, the returned string began with the model's
reasoning and ended with the answer.

It now collects answer chunks only, so the result matches the response object's
`content` instead of being roughly ten times longer.

The stream itself is unchanged — reasoning still arrives as events. A consumer
that calls `get_content()` on every item still folds the thinking into its own
output; branch on the type or on `metadata["type"]` (see
[Streaming and Callbacks](tutorials/streaming.md)).

## 12. The Leak Canary Actually Runs

`builtins/hooks.py` registers its completion matcher as an import side effect,
and nothing imported it — `load_amrita()` only loads MCP clients. The cookie
guard had therefore never run. `amrita_core.builtins` now imports it.

Two gaps in the guard itself are closed as well:

- **Reasoning is scanned.** The check only looked at the answer, so a model that
  quoted the canary while thinking passed. Reasoning is part of the model's
  output and is streamed to consumers, so it is checked too.
- **The persisted response is rewritten.** The runner stores whatever the
  completion event carries on the response object and in the conversation
  history. Substituting only the streamed payload left the canary reachable
  through `get_last_response()` and the next turn's context.

Chunks already delivered to a streaming consumer cannot be retracted; the error
payload appended to the stream is what marks the run as failed.

## 13. A Separate Output Budget for Compaction

The summary call used to inherit the chat preset's output ceiling. A reasoning
model spends its budget on thinking before it emits any content, so a small
`max_output` produced an empty summary and the fold silently did nothing.

`LLMConfig.compaction_max_tokens` (default `2048`) now raises the ceiling for
the summary call alone; set it to `0` to go back to inheriting the preset value.

The same starvation can hit an ordinary answer. When the provider returns
reasoning but no content and no tool calls, the framework now logs a warning
naming the cause instead of returning an empty reply with no explanation.

## 14. Inline Images Work on the Anthropic Path

The Anthropic adapter translated every `ImageContent` into an `image` block whose
`source.type` was `url`. The provider accepts three source variants and rejects a
`data:` URI sent as a `url` one, so an inline image failed the whole request with
`400 invalid url`:

```python
#  Broken before, works now
ImageContent(
    type="image_url",
    image_url=ImageUrl(url="data:image/png;base64,iVBORw0KGgo..."),
)
```

The adapter now picks the variant from the URL: an inline `data:` URI becomes a
`base64` source (with its media type), and anything else stays a `url` source.
External `http(s)` URLs behaved correctly before and are unchanged.

A `data:` URI that cannot become a `base64` source now raises `ValueError`
instead of being forwarded: a missing media type, a non-base64 payload and an
empty body each fail loudly rather than sending a request the model answers about
a picture it never received.

## Next

[API Reference](api-reference/index.md) — the full 1.0 surface, or
[Built-in Capabilities](builtins.md) — what ships in the box.
