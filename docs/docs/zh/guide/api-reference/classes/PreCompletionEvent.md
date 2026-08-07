# PreCompletionEvent

PreCompletionEvent 类表示在 agent 策略运行和模型完成之前触发的事件。

## 描述

PreCompletionEvent 继承自 `Event`，用于在事件钩子系统中在策略被调用之前拦截执行。其事件类型为 `EventTypeEnum.BEFORE_COMPLETION`。

## 属性

- `user_input`：用户的输入消息 (`USER_INPUT`)
- `original_context` (SendMessageWrap)：原始消息上下文
- `chat_object` (ChatObject)：驱动对话的 ChatObject 实例

## 继承的方法

- `get_event_type() -> EventTypeEnum`：返回 `EventTypeEnum.BEFORE_COMPLETION`
- `get_context_messages() -> SendMessageWrap`：返回当前消息上下文
- `get_user_input() -> USER_INPUT`：返回用户输入
- `message` (property)：获取或设置消息上下文

## 示例

```python
from amrita_core import on_precompletion
from amrita_core.hook.event import PreCompletionEvent


@on_precompletion
async def before_completion(event: PreCompletionEvent):
    # 在模型被调用之前修改消息上下文
    event.message = event.message
```
