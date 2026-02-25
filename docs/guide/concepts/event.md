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

## 3.3.7 Custom Parameter Injection

The `ChatObject` class supports injecting custom parameters through constructor arguments, which are passed to event handlers when events are triggered:

```python
from amrita_core.chatmanager import ChatObject

# Pass custom parameters when creating ChatObject
chat_obj = ChatObject(
    train={"system": "You are a helpful assistant"},
    user_input="Hello",
    context=None,
    session_id="session_123",
    hook_args=("custom_arg1", "custom_arg2"),
    hook_kwargs={"custom_key": "custom_value"}
)

# Receive these parameters in event handlers
@on_precompletion()
async def handle_pre_completion(event: PreCompletionEvent, *args, **kwargs):
    # args will contain ("custom_arg1", "custom_arg2")
    # kwargs will contain {"custom_key": "custom_value"}
    print(f"Custom args: {args}")
    print(f"Custom kwargs: {kwargs}")

# You can also specify exception types to ignore
chat_obj = ChatObject(
    train={"system": "You are a helpful assistant"},
    user_input="Hello",
    context=None,
    session_id="session_123",
    exception_ignored=(ValueError, TypeError)
)
```

### Parameter Description

- `hook_args`: Positional arguments tuple passed to event handlers
- `hook_kwargs`: Keyword arguments dictionary passed to event handlers
- `exception_ignored`: Tuple of exception types that should be ignored and raised again in event handlers

These parameters enable event handlers to access additional context information, enhancing the flexibility and extensibility of the event system.

## 3.3.8 Dependency Injection System (Depends)

AmritaCore provides a powerful dependency injection system that allows event handlers to declare their required dependencies, and the system automatically resolves and injects these dependencies.

### Depends Decorator

Use the `Depends` decorator to declare dependencies:

```python
from amrita_core.hook.matcher import Depends

async def get_database_connection():
    # Return database connection
    return database_connection

async def get_user_session(session_id: str):
    # Get user session based on session_id
    return user_session

@on_precompletion()
async def handle_with_dependencies(
    event: PreCompletionEvent,
    db_conn = Depends(get_database_connection),
    user_session = Depends(get_user_session)
):
    # The system will automatically call get_database_connection() and get_user_session()
    # and inject the results into the handler parameters
    user_data = await db_conn.get_user(user_session.user_id)
    event.messages.append(Message(
        role="system",
        content=f"User info: {user_data.name}"
    ))
```

### Concurrent Dependency Resolution

AmritaCore's dependency injection system supports **concurrent resolution** of multiple dependencies, significantly improving performance:

- All `Depends` declared dependencies are **executed concurrently**
- `DependsFactory` instances in positional arguments are resolved concurrently and updated at corresponding index positions
- `DependsFactory` instances in keyword arguments are resolved concurrently and updated at corresponding key positions
- If any dependency resolution fails (returns `None`), the entire event handler will be skipped

### Runtime Dependency Injection

In addition to declaring dependencies in function signatures, you can also pass `DependsFactory` instances at runtime through `hook_args` and `hook_kwargs`:

```python
from amrita_core.hook.matcher import Depends

# Create dependency at runtime
runtime_dependency = Depends(get_current_timestamp)

chat_obj = ChatObject(
    train={"system": "You are a helpful assistant"},
    user_input="What time is it now?",
    hook_args=(runtime_dependency,),
    hook_kwargs={"logger_dep": Depends(get_logger)}
)

@on_precompletion()
async def handle_runtime_deps(
    event: PreCompletionEvent,
    timestamp,  # Injected from hook_args
    logger_dep  # Injected from hook_kwargs
):
    logger_dep.info(f"Processing time: {timestamp}")
    event.messages.append(Message(
        role="system",
        content=f"Current time: {timestamp}"
    ))
```

### Dependency Resolution Rules

1. **Type Matching**: The dependency resolver automatically matches available dependencies based on parameter types
2. **Concurrent Execution**: All dependency resolution tasks are executed concurrently, avoiding serial bottlenecks
3. **Error Handling**:
   - If a dependency function throws an exception not in the `exception_ignored` list, it's collected into an `ExceptionGroup`
   - If a dependency function returns `None`, the entire event handler is skipped
   - If a dependency function throws an exception in the `exception_ignored` list, it's directly re-raised
4. **Context Isolation**: Each dependency resolution occurs in an isolated context, avoiding race conditions

### Best Practices

- **Async Dependencies**: Dependency functions can be async, and the system will automatically `await` the results
- **Cached Dependencies**: For expensive dependency computations, consider implementing caching within the dependency function
- **Type Annotations**: Add complete type annotations to dependency functions to ensure type safety
- **Error Handling**: Appropriately handle errors in dependency functions, returning `None` to indicate dependency unavailability

This dependency injection system allows event handlers to focus on business logic without worrying about dependency acquisition and management, while maintaining high performance and type safety.
