# FallbackContext

The `FallbackContext` class represents the context for preset fallback events when an LLM request fails.

## Constructor

```python
FallbackContext(
    preset: ModelPreset,
    exc_info: BaseException,
    config: AmritaConfig,
    context: SendMessageWrap,
    term: int
)
```

## Properties

### preset

- **Type**: [`ModelPreset`](./ModelPreset.md)
- **Description**: The current model preset being used for the failed request.

### exc_info

- **Type**: `BaseException`
- **Description**: The exception that caused the LLM request to fail.

### config

- **Type**: [`AmritaConfig`](./AmritaConfig.md)
- **Description**: The current Amrita configuration.

### context

- **Type**: [`SendMessageWrap`](./SendMessageWrap.md)
- **Description**: The message context that was being sent when the failure occurred.

### term

- **Type**: `int`
- **Description**: The current retry attempt number (starting from 1).

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
from amrita_core.hook.event import FallbackContext
from amrita_core.hook.on import on_preset_fallback

@on_preset_fallback()
async def handle_fallback(event: FallbackContext):
    print(f"Request failed: {event.exc_info}")
    if event.term == 1:
        # Switch to alternative preset on first retry
        event.preset = get_alternative_preset()
    else:
        # Fail on subsequent retries
        event.fail("No more fallback options")
```
