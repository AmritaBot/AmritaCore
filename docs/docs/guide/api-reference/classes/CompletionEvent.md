# CompletionEvent

The CompletionEvent class represents the event fired after model completion.

## Description

CompletionEvent inherits from `Event` and carries the model's response. Its event type is `EventTypeEnum.COMPLETION`. It is used by the event hook system to observe or modify the result of a completed model call.

## Properties

- `model_response` (str): The raw text response from the model
- `user_input`: The user's input message (`USER_INPUT`)
- `original_context` (SendMessageWrap): The original message context
- `chat_object` (ChatObject): The ChatObject instance driving the conversation

## Methods

- `get_model_response() -> str`: Returns the model's response text
- `get_event_type() -> EventTypeEnum`: Returns `EventTypeEnum.COMPLETION`

## Example

```python
from amrita_core import on_completion
from amrita_core.hook.event import CompletionEvent

@on_completion
async def handle_completion(event: CompletionEvent):
    response = event.get_model_response()
    print(f"Model replied: {response}")
```
