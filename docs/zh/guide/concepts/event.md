# 事件系统

## 3.3.1 事件驱动设计

AmritaCore 实现了一个事件驱动架构，允许您在处理流水线的各个阶段拦截和修改。可以注册事件以响应特定条件或操作。

## 3.3.2 PreCompletionEvent 预完成事件

[PreCompletionEvent](../api-reference/classes/PreCompletionEvent.md) 在完成请求发送到 LLM 之前触发：

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion()
async def handle_pre_completion(event: PreCompletionEvent):
    # 在发送到 LLM 之前修改消息
    event.messages.append(Message(role="system", content="始终乐于助人"))
    # 动态修改预设
    event.chat_object.preset = get_new_preset()

```

## 3.3.3 CompletionEvent 完成事件

[CompletionEvent](../api-reference/classes/CompletionEvent.md) 在从 LLM 接收完成响应后触发：

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion()
async def handle_completion(event: CompletionEvent):
    # 在返回给用户之前处理响应
    print(f"收到响应: {event.response}")

```

## 3.3.4 FallbackContext 预设回退事件

[FallbackContext](../api-reference/classes/FallbackContext.md) 在 LLM 请求失败且需要回退机制时触发。此事件允许您通过切换到替代模型预设或实现自定义重试逻辑来优雅地处理失败。

```python
from amrita_core.hook.event import FallbackContext
from amrita_core.hook.on import on_preset_fallback

@on_preset_fallback()
async def handle_fallback(event: FallbackContext):
    # 处理 LLM 请求失败
    print(f"LLM 请求失败，错误信息: {event.exc_info}")
    print(f"当前预设: {event.preset.name}")

    # 切换到不同的预设进行重试
    # 系统将自动使用 event.preset 进行下一次尝试
    if event.term == 1:  # 第一次重试
        event.preset = get_alternative_preset()  # 您的自定义函数获取替代预设
    elif event.term == 2:  # 第二次重试
        event.preset = get_safe_preset()  # 您的自定义函数获取安全/更便宜的预设
    else:
        # 如果没有更多回退选项，标记为失败
        event.fail("没有更多可用的回退预设")

```

`FallbackContext` 提供以下属性：

- `preset`: 当前使用的 [ModelPreset](../api-reference/classes/ModelPreset.md)
- `exc_info`: 导致失败的异常信息
- `config`: 当前的 [AmritaConfig](../api-reference/classes/AmritaConfig.md)
- `context`: 包含消息上下文的 [SendMessageWrap](../api-reference/classes/SendMessageWrap.md)
- `term`: 当前重试尝试次数（从 1 开始）

您可以修改 `event.preset` 来切换到不同的模型预设进行下一次重试尝试。如果没有合适的回退选项，调用 `event.fail(reason)` 来终止重试过程。

## 3.3.5 MatcherManager 事件匹配器

[MatcherManager](../api-reference/classes/MatcherManager.md) 负责将事件匹配到相应的处理器：

```python
from amrita_core.hook.matcher import MatcherManager

# 匹配器在内部用于将事件路由到处理器
matcher = MatcherManager()
```

## 3.3.6 事件注册与触发

事件使用装饰器注册，并在处理流水线中自动触发：

```python
from amrita_core.hook.on import on_event

@on_event()
def my_custom_handler(event):
    # 处理自定义事件
    pass
```

## 3.3.7 事件钩子（Event Hooks）

有多种类型的事件钩子可用：

- `@on_precompletion`: 在发送请求到 LLM 之前
- `@on_completion`: 在从 LLM 接收响应之后
- `@on_preset_fallback`: 在 LLM 尝试失败时的预设回退处理
- `@on_event`: 用于自定义事件

## 3.3.8 自定义参数注入

`ChatObject` 类支持通过构造函数参数注入自定义参数，这些参数会在事件触发时传递给事件处理器：

```python
from amrita_core.chatmanager import ChatObject

class MyClass:
    ...

class MyObject:
    ...


# 创建 ChatObject 时传入自定义参数
chat_obj = ChatObject(
    train={"system": "你是一个有用的助手"},
    user_input="你好",
    context=None,
    session_id="session_123",
    hook_args=(MyClass(), MyObject()),
    hook_kwargs={"custom_key": "custom_value"}
)

# 在事件处理器中接收这些参数
@on_precompletion()
async def handle_pre_completion(event: PreCompletionEvent, arg1: MyClass, arg2: MyObject, custom_key: str):
    ...


# 也可以指定异常忽略列表(忽略的异常触发时，会被重新抛出)
chat_obj = ChatObject(
    train={"system": "你是一个有用的助手"},
    user_input="你好",
    context=None,
    session_id="session_123",
    exception_ignored=(ValueError, TypeError)
)
```

### 参数说明

- `hook_args`: 传递给事件处理器的位置参数元组
- `hook_kwargs`: 传递给事件处理器的关键字参数字典
- `exception_ignored`: 指定在事件处理器中应该被忽略并重新抛出的异常类型

这些参数使得事件处理器能够访问额外的上下文信息，增强了事件系统的灵活性和可扩展性。

::: warning
函数签名内不能使用`*args`或`**kwargs`，它们可能会使得AmritaCore无法正常解析函数签名，从而直接跳过此`Matcher`。
:::

## 3.3.9 依赖注入系统 (Depends)

AmritaCore 提供了强大的依赖注入系统，允许事件处理器声明它们所需的依赖项，系统会自动解析并注入这些依赖。

### Depends 装饰器

使用 `Depends` 装饰器来声明依赖项：

```python
from amrita_core.hook.matcher import Depends

async def get_database_connection():
    # 返回数据库连接
    return database_connection

async def get_user_session(session_id: str):
    # 根据 session_id 获取用户会话
    return user_session

@on_precompletion()
async def handle_with_dependencies(
    event: PreCompletionEvent,
    db_conn = Depends(get_database_connection),
    user_session = Depends(get_user_session)
):
    # 系统会自动调用 get_database_connection() 和 get_user_session()
    # 并将结果注入到处理器参数中
    user_data = await db_conn.get_user(user_session.user_id)
    event.messages.append(Message(
        role="system",
        content=f"用户信息: {user_data.name}"
    ))
```

### 并发依赖解析

AmritaCore 的依赖注入系统支持**并发解析**多个依赖项，显著提高性能：

- 所有 `Depends` 声明的依赖项会**并发执行**
- 位置参数中的 `DependsFactory` 实例会被并发解析并更新到对应索引位置
- 关键字参数中的 `DependsFactory` 实例会被并发解析并更新到对应键位置
- 如果任何依赖解析失败（返回 `None`），整个事件处理器将被跳过

### 运行时依赖注入

除了在函数签名中声明依赖，还可以在运行时通过 `hook_args` 和 `hook_kwargs` 传递 `DependsFactory` 实例：

```python
from amrita_core.hook.matcher import Depends

# 在运行时创建依赖
runtime_dependency = Depends(get_current_timestamp) # 我们先假定这个`get_current_timestamp`函数返回类型为`MyTimestamp`的对象

chat_obj = ChatObject(
    train={"system": "你是一个有用的助手"},
    user_input="现在几点了？",
    hook_args=(runtime_dependency,),
    hook_kwargs={"logger_dep": Depends(get_logger)}
)

@on_precompletion()
async def handle_runtime_deps(
    event: PreCompletionEvent,
    timestamp: MyTimestamp,  # 从 hook_args 注入
    logger_dep  # 从 hook_kwargs 注入
):
    logger_dep.info(f"处理时间: {timestamp}")
    event.messages.append(Message(
        role="system",
        content=f"当前时间: {timestamp}"
    ))
```

### 依赖解析规则

1. **类型匹配**: 依赖解析器会根据参数类型自动匹配可用的依赖
2. **并发执行**: 所有依赖解析任务并发执行，避免串行瓶颈
3. **错误处理**:
   - 如果依赖函数抛出异常且不在 `exception_ignored` 列表中，会收集到 `ExceptionGroup`
   - 如果依赖函数返回 `None`，整个事件处理器会被跳过
   - 如果依赖函数在 `exception_ignored` 列表中抛出异常，会直接重新抛出
4. **上下文隔离**: 每个依赖解析都在独立的上下文中进行，避免竞态条件

:::tip
如果存在一个参数，它只能通过位置参数传递，那么您需要确保该参数（函数签名内）拥有**类型注解**，否则此Matcher会被忽略。

e.g.

```python
chatobj = ChatObject(
    ...
    ,hook_args=(MyObject(),)
)
...
@on_precompletion()
async def handle_with_dependencies(arg1,):... # 此handler会被忽略，因为arg1没有类型注解，并且关键词参数内也不存在此参数。

@on_precompletion()
async def handle_with_dependencies(arg1:MyObject):... # 正确，它声明了arg1的类型注解，并且的确存在一个MyObject类型的位置参数


:::

### 最佳实践

- **异步依赖**: 依赖函数可以是异步的，系统会自动 `await` 结果
- **缓存依赖**: 对于昂贵的依赖计算，考虑在依赖函数内部实现缓存
- **类型注解**: 为依赖函数添加完整的类型注解，确保类型安全
- **错误处理**: 在依赖函数中适当处理错误，返回 `None` 表示依赖不可用

这个依赖注入系统使得事件处理器可以专注于业务逻辑，而不需要关心依赖的获取和管理，同时保持高性能和类型安全。
```
