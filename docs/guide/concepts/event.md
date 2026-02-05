# Event System

## 3.3.1 Event-Driven Design

AmritaCore implements an event-driven architecture that allows you to intercept and modify the processing pipeline at various stages. Events can be registered to respond to specific conditions or actions.

## 3.3.2 PreCompletionEvent Pre-Completion Event

The [PreCompletionEvent](../api-reference/classes/PreCompletionEvent.md) is triggered before the completion request is sent to the LLM:

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion()
async def handle_pre_completion(event: PreCompletionEvent):
    # Modify the messages before sending to LLM
    event.messages.append(Message(role="system", content="Always be helpful"))
    
```

## 3.3.3 CompletionEvent Completion Event

The [CompletionEvent](../api-reference/classes/CompletionEvent.md) is triggered after receiving the completion from the LLM:

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion()
async def handle_completion(event: CompletionEvent):
    # Process the response before returning to user
    print(f"Received response: {event.response}")
    
```

## 3.3.4 MatcherManager Event Matcher

The [MatcherManager](../api-reference/classes/MatcherManager.md) handles matching events to appropriate handlers:

```python
from amrita_core.hook.matcher import MatcherManager

# The matcher is used internally to route events to handlers
matcher = MatcherManager()
```

## 3.3.5 Event Registration and Triggering

Events are registered using decorators and automatically triggered during the processing pipeline:

```python
from amrita_core.hook.on import on_event

@on_event()
def my_custom_handler(event):
    # Handle custom events
    pass
```

## 3.3.6 Event Hooks (Event Hooks)

Multiple types of event hooks are available:

- `@on_precompletion`: Before sending request to LLM
- `@on_completion`: After receiving response from LLM
- `@on_event`: For custom events
- `@on_tools`: For tool-related events