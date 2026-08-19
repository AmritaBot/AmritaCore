# FallbackContext

The `FallbackContext` class is the **base class** for all preset-fallback events fired by the `libchat` gateway layer (`call_completion`, `tools_caller`, `call_embedding`) when a request fails. It represents the context of a preset fallback event and carries the information needed to switch to an alternative preset.

Every fallback event shares the `PRESET_FALLBACK` event type; concrete subclasses distinguish the failing gateway call so matchers can react differently to each kind.

## Class Hierarchy

```text
FallbackContext (base)
├── CompletionFallbackContext  # call_completion fails
├── ToolsFallbackContext       # tools_caller fails
└── EmbeddingFallbackContext   # call_embedding fails
```

## Constructor

```python
FallbackContext(
    preset: ModelPreset,
    exc_info: BaseException,
    config: AmritaConfig,
    context: SendMessageWrap | CONTENT_LIST_TYPE | Sequence[str],
    term: int
)
```

## Properties

### preset

- **Type**: [`ModelPreset`](./ModelPreset.md)
- **Description**: The current model preset being used for the failed request.

### exc_info

- **Type**: `BaseException`
- **Description**: The exception that caused the request to fail.

### config

- **Type**: [`AmritaConfig`](./AmritaConfig.md)
- **Description**: The current Amrita configuration.

### context

- **Type**: `SendMessageWrap | CONTENT_LIST_TYPE | Sequence[str]`
- **Description**: The payload of the failed call. The concrete type depends on the subclass:
  - `CompletionFallbackContext`: validated message list (`CONTENT_LIST_TYPE`)
  - `ToolsFallbackContext`: validated message list (`CONTENT_LIST_TYPE`)
  - `EmbeddingFallbackContext`: input text sequence (`Sequence[str]`)

### term

- **Type**: `int`
- **Description**: The current fallback attempt number (starting from 1).

## Subclasses

### CompletionFallbackContext

Fired when `call_completion` fails. `context` carries the validated message list (`CONTENT_LIST_TYPE`).

### ToolsFallbackContext

Fired when `tools_caller` fails. In addition to `context`, it exposes:

- `tools` (`list[ToolFunctionSchema] | None`): the tool schemas of the failed call.

### EmbeddingFallbackContext

Fired when `call_embedding` fails. `context` carries the input text sequence (`Sequence[str]`).

## Methods

### fail(reason: Any | None = None) -> Never

Mark the event as failed and terminate the retry process.

**Parameters**:

- `reason` (Any | None): Optional reason for the failure.

**Raises**:

- [`FallbackFailed`](../exceptions/FallbackFailed.md): Always raises this exception to terminate the fallback process.

### get_event_type() -> EventTypeEnum

Get the event type enum value.

**Returns**:

- `EventTypeEnum.PRESET_FALLBACK`

## Example Usage

```python
from amrita_core.hook.event import CompletionFallbackContext, FallbackContext
from amrita_core.hook.on import on_preset_fallback


@on_preset_fallback().handle()
async def handle_fallback(event: FallbackContext):
    print(f"Request failed: {event.exc_info}")
    if event.term == 1:
        # Switch to alternative preset on first retry
        event.preset = get_alternative_preset()
    else:
        # Fail on subsequent retries
        event.fail("No more fallback options")


@on_preset_fallback().handle()
async def handle_tools_fallback(event: ToolsFallbackContext):
    # Differentiate between fallback kinds
    print(f"Tool call failed: {event.tools}")
    event.preset = get_fallback_preset()
```
