# Depends

`Depends` is a decorator function used to declare dependencies in event handlers. It automatically creates `DependsFactory` instances and integrates them into AmritaCore's dependency injection system.

## Function Signature

```python
def Depends(dependency: Callable[..., T | Awaitable[T]]) -> Any
```

**Parameters**:

- `dependency`: The dependency function to inject, which can return any type `T` or an awaitable object `Awaitable[T]`

**Returns**:

- `Any`: Returns a `DependsFactory[T]` instance for the dependency injection system

## Usage Examples

### Basic Usage

```python
from amrita_core.hook.matcher import Depends

async def get_current_user():
    # Get current user information
    return current_user

@on_precompletion()
async def handle_with_user(
    event: PreCompletionEvent,
    user = Depends(get_current_user)
):
    # The user parameter will be automatically injected with the return value of get_current_user()
    event.messages.append(Message(
        role="system",
        content=f"Current user: {user.name}"
    ))
```

### Multiple Dependencies

```python
async def get_database():
    return database_connection

async def get_logger():
    return logger_instance

@on_completion()
async def handle_with_multiple_deps(
    event: CompletionEvent,
    db = Depends(get_database),
    logger = Depends(get_logger)
):
    # Both dependencies will be resolved concurrently and injected
    logger.info("Processing completion event")
    await db.log_response(event.response)
```

### Runtime Dependencies

```python
# Create dependency at runtime
runtime_dep = Depends(get_timestamp)

chat_obj = ChatObject(
    train={"system": "Assistant"},
    user_input="What time?",
    hook_kwargs={"timestamp": runtime_dep}
)

@on_precompletion()
async def handle_runtime_dep(event, timestamp):
    # timestamp will be automatically injected
    event.messages.append(Message(
        role="system",
        content=f"Current time: {timestamp}"
    ))
```

## How It Works

1. **Declaration Phase**: When the event handler function is defined, the `Depends` decorator creates `DependsFactory` instances
2. **Registration Phase**: When the event handler is registered to the event system, these `DependsFactory` instances are identified
3. **Resolution Phase**: When the event is triggered, all `DependsFactory` instances are **resolved concurrently**
4. **Injection Phase**: The resolution results are injected into the corresponding function parameter positions

## Notes

- Dependency functions can be synchronous or asynchronous
- All dependency resolutions are executed concurrently for improved performance
- If any dependency returns `None`, the entire event handler will be skipped
- Using `Depends` decorator inside a dependency function is not allowed (to avoid circular dependencies)
- For best type safety, it's recommended to add complete type annotations to dependency functions
