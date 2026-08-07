# PreCompletionEvent

The PreCompletionEvent class represents the event fired before the agent strategy runs and model completion.

## Description

PreCompletionEvent inherits from `Event` and is used in the event hook system to intercept execution before the strategy is invoked. Its event type is `EventTypeEnum.BEFORE_COMPLETION`.

## Properties

- `user_input`: The user's input message (`USER_INPUT`)
- `original_context` (SendMessageWrap): The original message context
- `chat_object` (ChatObject): The ChatObject instance driving the conversation

## Inherited Methods

- `get_event_type() -> EventTypeEnum`: Returns `EventTypeEnum.BEFORE_COMPLETION`
- `get_context_messages() -> SendMessageWrap`: Returns the current message context
- `get_user_input() -> USER_INPUT`: Returns the user input
- `message` (property): Get or set the message context; setter validates `SendMessageWrap` type

## Example

```python
from amrita_core import on_precompletion
from amrita_core.hook.event import PreCompletionEvent


@on_precompletion
async def before_completion(event: PreCompletionEvent):
    # Modify the message context before the model is called
    event.message = event.message  # or build a new SendMessageWrap
```
