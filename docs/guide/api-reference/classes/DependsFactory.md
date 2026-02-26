# DependsFactory

The `DependsFactory` class is the core component of AmritaCore's dependency injection system, used to wrap dependency functions and provide resolution capabilities.

## Constructor

```python
def __init__(self, depency: Callable[..., T | Awaitable[T]])
```

- `depency`: The dependency function to wrap, which can return any type `T` or an awaitable object `Awaitable[T]`

## Methods

### resolve

```python
async def resolve(self, *args, **kwargs) -> T | None
```

Resolves the dependency and returns the result.

**Parameters**:

- `*args`: Positional arguments passed to the dependency function
- `**kwargs`: Keyword arguments passed to the dependency function

**Returns**:

- `T | None`: The return value of the dependency function, or `None` if resolution fails

**Exceptions**:

- Raises `RuntimeError` if the dependency function uses `Depends` decorator internally

## Usage Example

```python
from amrita_core.hook.matcher import DependsFactory

async def get_database_connection():
    # Return database connection
    return database_connection

# Create DependsFactory instance
db_factory = DependsFactory(get_database_connection)

# Manually resolve dependency
db_conn = await db_factory.resolve()
```

## Notes

- `DependsFactory` is typically created automatically through the `Depends` decorator, direct instantiation is not recommended
- Dependency functions can be synchronous or asynchronous, the `resolve` method handles both automatically
- If the dependency function returns `None`, it indicates the dependency is unavailable
- Using `Depends` decorator inside a dependency function will cause circular dependencies and is not allowed
