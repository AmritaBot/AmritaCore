# Depends

`Depends` 是一个装饰器函数，用于在事件处理器中声明依赖项。它会自动创建 `DependsFactory` 实例并集成到 AmritaCore 的依赖注入系统中。

## 函数签名

```python
def Depends(dependency: Callable[..., T | Awaitable[T]]) -> Any
```

**参数**:

- `dependency`: 要注入的依赖函数，可以返回任意类型 `T` 或异步可等待对象 `Awaitable[T]`

**返回值**:

- `Any`: 返回 `DependsFactory[T]` 实例，用于依赖注入系统

## 使用示例

### 基本用法

```python
from amrita_core.hook.matcher import Depends

async def get_current_user():
    # 获取当前用户信息
    return current_user

@on_precompletion()
async def handle_with_user(
    event: PreCompletionEvent,
    user = Depends(get_current_user)
):
    # user 参数会自动注入 get_current_user() 的返回值
    event.messages.append(Message(
        role="system",
        content=f"当前用户: {user.name}"
    ))
```

### 多个依赖

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
    # 两个依赖都会被并发解析和注入
    logger.info("处理完成事件")
    await db.log_response(event.response)
```

### 运行时依赖

```python
# 在运行时创建依赖
runtime_dep = Depends(get_timestamp)

chat_obj = ChatObject(
    train={"system": "助手"},
    user_input="时间？",
    hook_kwargs={"timestamp": runtime_dep}
)

@on_precompletion()
async def handle_runtime_dep(event, timestamp):
    # timestamp 会被自动注入
    event.messages.append(Message(
        role="system",
        content=f"当前时间: {timestamp}"
    ))
```

## 工作原理

1. **声明阶段**: 当事件处理器函数定义时，`Depends` 装饰器创建 `DependsFactory` 实例
2. **注册阶段**: 事件处理器注册到事件系统时，这些 `DependsFactory` 实例被识别
3. **解析阶段**: 事件触发时，所有 `DependsFactory` 实例被**并发解析**
4. **注入阶段**: 解析结果被注入到对应的函数参数位置

## 注意事项

- 依赖函数可以是同步或异步的
- 所有依赖解析都是并发执行的，提高性能
- 如果任何依赖返回 `None`，整个事件处理器会被跳过
- 依赖函数内部不能使用 `Depends` 装饰器（避免循环依赖）
- 为获得最佳类型安全，建议为依赖函数添加完整的类型注解
