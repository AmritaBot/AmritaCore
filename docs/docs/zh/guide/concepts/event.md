# 事件系统

> **自 v0.9.0rc1 起**：事件系统核心（`BaseEvent`、`MatcherFactory`、`EventRegistry`、`MatcherException`、`CancelException`、`PassException`）已迁移至 [AmritaSense](https://sense.amritabot.com)。完整文档见 [AmritaSense 事件系统](https://sense.amritabot.com/guide/advanced/event_system)。`amrita_core.hook.*` 兼容性端点已在 v0.10.x+ 中移除；请直接从 `amrita_sense` 导入。

## 事件驱动设计

AmritaCore 实现了事件驱动架构，允许你在处理管道的各个阶段拦截和修改处理过程。事件可以注册以响应特定条件或操作。

## PreCompletionEvent 前置完成事件

[PreCompletionEvent](../api-reference/classes/PreCompletionEvent.md) 在完成请求发送给 LLM 之前触发：

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion().handle()
async def handle_pre_completion(event: PreCompletionEvent):
    # 在发送给 LLM 之前修改消息
    event.message.memory.append(Message(role="system", content="始终乐于助人"))
    # 动态修改 preset
    event.chat_object.preset = get_new_preset()
```

## CompletionEvent 完成事件

[CompletionEvent](../api-reference/classes/CompletionEvent.md) 在收到 LLM 的完成响应后触发：

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion().handle()
async def handle_completion(event: CompletionEvent):
    # 在返回给用户之前处理响应
    print(f"收到响应：{event.get_model_response()}")
```

## FallbackContext Preset 回退事件

[FallbackContext](../api-reference/classes/FallbackContext.md) 在 LLM 请求失败需要回退机制时触发。此事件允许你通过切换到替代模型预设或实现自定义重试逻辑来优雅地处理失败。

```python
from amrita_core.hook.event import FallbackContext
from amrita_core.hook.on import on_preset_fallback

@on_preset_fallback().handle()
async def handle_fallback(event: FallbackContext):
    # 处理 LLM 请求失败
    print(f"LLM 请求失败，错误：{event.exc_info}")
    print(f"当前预设：{event.preset.name}")

    # 切换到其他预设进行重试
    # 系统将自动使用 event.preset 进行下一次尝试
    if event.term == 0:  # 首次尝试
        event.preset = get_alternative_preset()  # 自定义函数获取替代预设
    elif event.term == 1:  # 第一次重试
        event.preset = get_safe_preset()  # 自定义函数获取安全/更便宜的预设
    else:
        # 如果没有更多回退可用，标记为失败
        event.fail("没有更多可用的回退预设")
```

`FallbackContext` 提供以下属性：

- `preset`：当前使用的 [ModelPreset](../api-reference/classes/ModelPreset.md)
- `exc_info`：导致失败的异常
- `config`：当前的 [AmritaConfig](../api-reference/classes/AmritaConfig.md)
- `context`：包含消息上下文的 [SendMessageWrap](../api-reference/classes/SendMessageWrap.md)
- `term`：当前重试次数，从 **0**（首次调用）到 `max_retries - 1`

你可以修改 `event.preset` 以切换到不同的模型预设进行下次重试。如果没有合适的回退可用，调用 `event.fail(reason)` 终止重试过程。

## MatcherManager 事件匹配器

> **注意**：自 v0.9.0rc1 起，`MatcherManager`（`MatcherFactory`）已移至 `amrita-sense` 包。`amrita_core.hook.matcher` 兼容性端点已在 v0.10.x+ 中移除；请直接从 `amrita_sense` 导入。

`MatcherManager` 负责将事件匹配到适当的处理器：

```python
# 从 amrita-sense 导入
from amrita_sense.hook.matcher import MatcherFactory
```

## 事件注册与触发

事件通过装饰器注册，并在处理管道中自动触发：

```python
from amrita_core.hook.on import on_event

@on_event()
def my_custom_handler(event):
    # 处理自定义事件
    pass
```

## 事件钩子

提供多种类型的事件钩子：

- `@on_precompletion`：发送请求给 LLM 之前
- `@on_completion`：收到 LLM 响应之后
- `@on_preset_fallback`：LLM 请求失败时
- `@on_event`：自定义事件

## 自定义参数注入

`ChatObject` 类支持通过构造函数参数注入自定义参数，这些参数在事件触发时传递给事件处理器：

```python
from amrita_core.chatmanager import ChatObject

class MyClass:
    ...

class MyObject:
    ...

# 创建 ChatObject 时传递自定义参数
chat_obj = ChatObject(
    train={"system": "你是一个乐于助人的助手"},
    user_input="你好",
    context=None,
    session_id="session_123",
    hook_args=(MyClass(), MyObject()),
    hook_kwargs={"custom_key": "custom_value"}
)

# 在事件处理器中接收这些参数
@on_precompletion().handle()
async def handle_pre_completion(event: PreCompletionEvent, arg1: MyClass, arg2: MyObject, custom_key: str):
    ...

# 你也可以指定要忽略的异常类型（被忽略的异常将重新抛出）
chat_obj = ChatObject(
    train={"system": "你是一个乐于助人的助手"},
    user_input="你好",
    context=None,
    session_id="session_123",
    exception_ignored=(ValueError, TypeError)
)
```

### 参数说明

- `hook_args`：传递给事件处理器的位置参数元组
- `hook_kwargs`：传递给事件处理器的关键字参数字典
- `exception_ignored`：应在事件处理器中被忽略并重新抛出的异常类型元组

这些参数使事件处理器能够访问附加上下文信息，增强事件系统的灵活性和可扩展性。

::: warning
函数签名不能使用 `*args` 或 `**kwargs`，因为它们可能阻止 AmritaCore 正确解析函数签名，导致 `Matcher` 被跳过。
:::

## 依赖注入系统（Depends）

AmritaCore 提供了强大的依赖注入系统，允许事件处理器声明它们需要的依赖，系统会自动解析并注入这些依赖。

### 什么是依赖注入？

**依赖注入（DI）** 是一种设计模式，对象从外部源接收其依赖，而不是在内部创建它们。在 AmritaCore 中：

- **依赖** 是事件处理器需要的资源（如数据库连接、API 客户端、配置对象等）
- **注入** 意味着 AmritaCore 在处理器函数被调用时自动提供这些资源
- **优势**：
  - 处理器函数无需知道如何创建或管理这些资源
  - 资源可以轻松共享、缓存或模拟
  - 代码变得更易于测试和维护
  - 复杂的设置逻辑集中在依赖函数中

使用 AmritaCore 的 DI 系统，你只需声明需要什么：

```python
# 使用 DI — 自动资源注入
@on_precompletion().handle()
async def handle_with_dependencies(
    event: PreCompletionEvent,
    db_conn = Depends(get_database_connection),
    user_session = Depends(get_user_session)
):
    # 资源自动提供！
    # ... 直接使用资源
```

### Depends 装饰器

使用 `Depends` 声明依赖：

```python
from amrita_core.hook.matcher import Depends

async def get_database_connection():
    # 返回数据库连接
    return database_connection

async def get_user_session(session_id: str):
    # 根据 session_id 获取用户会话
    return user_session

@on_precompletion().handle()
async def handle_with_dependencies(
    event: PreCompletionEvent,
    db_conn = Depends(get_database_connection),
    user_session = Depends(get_user_session)
):
    # 系统将自动调用 get_database_connection() 和 get_user_session()
    # 并将结果注入处理器参数
    user_data = await db_conn.get_user(user_session.user_id)
    event.messages.append(Message(
        role="system",
        content=f"用户信息：{user_data.name}"
    ))
```

### 用于授权和验证的依赖注入

**重要**：如果任何依赖函数返回 `None` 或引发异常（不在 `exception_ignored` 列表中），**整个事件处理器将被自动跳过**。此行为使依赖注入非常适合**授权和权限验证**。

#### 权限验证示例

你可以使用依赖注入实现权限检查：

```python
async def require_admin_permission(session_id: str):
    """仅为管理员用户返回值的依赖"""
    user = get_user_from_session(session_id)
    if user.is_admin:
        return user  # 管理员用户 — 允许处理器继续
    else:
        return None  # 非管理员用户 — 跳过此处理器

async def validate_api_key(api_key: str):
    """验证 API 密钥的依赖"""
    if is_valid_api_key(api_key):
        return api_key  # 有效密钥 — 允许处理器继续
    else:
        return None  # 无效密钥 — 跳过此处理器

# 此处理器仅对具有有效 API 密钥的管理员用户执行
@on_precompletion().handle()
async def admin_only_handler(
    event: PreCompletionEvent,
    admin_user = Depends(require_admin_permission),
    valid_key = Depends(validate_api_key)
):
    # 仅当两个依赖都成功时此代码才运行
    event.messages.append(Message(
        role="system",
        content="管理员模式已激活"
    ))
```

::: tip
对于授权场景，当验证失败时始终从依赖函数返回 `None`。返回任何其他假值（如 `False` 或空字符串）仍会导致处理器执行。

**注意**：如果任何运行时依赖返回 `None`，事件处理管道将以异常结束。
:::

### 并发依赖解析

AmritaCore 的依赖注入系统支持**并发解析**多个依赖，显著提高性能：

- 所有 `Depends` 声明的依赖**并发执行**
- 位置参数中的 `DependsFactory` 实例并发解析并在相应索引位置更新
- 关键字参数中的 `DependsFactory` 实例并发解析并在相应键位置更新
- 如果任何依赖解析失败（返回 `None`），整个事件处理器将被跳过

### 运行时依赖注入

除了在函数签名中声明依赖外，你还可以在运行时通过 `hook_args` 和 `hook_kwargs` 传递 `DependsFactory` 实例：

```python
from amrita_core.hook.matcher import Depends

# 在运行时创建依赖
runtime_dependency = Depends(get_current_timestamp)

chat_obj = ChatObject(
    train={"system": "你是一个有帮助的助手"},
    user_input="现在几点了？",
    hook_args=(runtime_dependency,),
    hook_kwargs={"logger_dep": Depends(get_logger)}
)

@on_precompletion().handle()
async def handle_runtime_deps(
    event: PreCompletionEvent,
    timestamp: MyTimestamp,  # 从 hook_args 注入
    logger_dep               # 从 hook_kwargs 注入
):
    logger_dep.info(f"处理时间：{timestamp}")
    event.messages.append(Message(
        role="system",
        content=f"当前时间：{timestamp}"
    ))
```

### 依赖解析规则

1. **类型匹配**：依赖解析器根据参数类型自动匹配合适的依赖
2. **并发执行**：所有依赖解析任务并发执行，避免串行瓶颈
3. **错误处理**：
   - 如果依赖函数抛出不在 `exception_ignored` 列表中的异常，将被收集到 `ExceptionGroup` 中
   - 如果依赖函数返回 `None`，整个事件处理器将被跳过
   - 如果依赖函数抛出在 `exception_ignored` 列表中的异常，将直接重新抛出
4. **上下文隔离**：每次依赖解析在隔离的上下文中进行，避免竞态条件

:::tip
如果有一个只能作为位置参数传递的参数，你需要确保该参数在函数签名中有**类型注解**，否则此 Matcher 将被忽略。
:::

### 最佳实践

- **异步依赖**：依赖函数可以是异步的，系统将自动 `await` 结果
- **缓存依赖**：对于昂贵的依赖计算，考虑在依赖函数内实现缓存
- **类型注解**：为依赖函数添加完整的类型注解以确保类型安全
- **错误处理**：在依赖函数中适当处理错误，返回 `None` 表示依赖不可用

此依赖注入系统使事件处理器能够专注于业务逻辑，无需担心依赖的获取和管理，同时保持高性能和类型安全。
