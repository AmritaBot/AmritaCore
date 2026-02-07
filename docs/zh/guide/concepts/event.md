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

## 3.3.4 MatcherManager 事件匹配器

[MatcherManager](../api-reference/classes/MatcherManager.md) 处理将事件匹配到适当的处理器：

```python
from amrita_core.hook.matcher import MatcherManager

# 匹配器在内部用于将事件路由到处理器
matcher = MatcherManager()
```

## 3.3.5 事件注册和触发

事件使用装饰器注册，并在处理流水线期间自动触发：

```python
from amrita_core.hook.on import on_event

@on_event()
def my_custom_handler(event):
    # 处理自定义事件
    pass
```

## 3.3.6 事件钩子（Event Hooks）

有多种类型的事件钩子可用：

- `@on_precompletion`: 在发送请求到 LLM 之前
- `@on_completion`: 在从 LLM 接收响应之后
- `@on_event`: 用于自定义事件
- `@on_tools`: 用于工具相关事件