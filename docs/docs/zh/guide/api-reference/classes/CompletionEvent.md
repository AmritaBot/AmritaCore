# CompletionEvent

CompletionEvent 类表示模型完成调用后触发的事件。

## 描述

CompletionEvent 继承自 `Event`，携带模型的响应。其事件类型为 `EventTypeEnum.COMPLETION`。它被事件钩子系统用于观测或修改已完成的模型调用结果。

## 属性

- `model_response` (str)：模型的原始文本响应
- `user_input`：用户的输入消息 (`USER_INPUT`)
- `original_context` (SendMessageWrap)：原始消息上下文
- `chat_object` (ChatObject)：驱动对话的 ChatObject 实例

## 方法

- `get_model_response() -> str`：返回模型的响应文本
- `get_event_type() -> EventTypeEnum`：返回 `EventTypeEnum.COMPLETION`

## 示例

```python
from amrita_core import on_completion
from amrita_core.hook.event import CompletionEvent

@on_completion
async def handle_completion(event: CompletionEvent):
    response = event.get_model_response()
    print(f"模型回复: {response}")
```
