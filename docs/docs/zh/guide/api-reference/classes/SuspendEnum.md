# SuspendEnum

`SuspendEnum` 类为 AmritaCore 中的挂起/恢复机制提供标准化的断点标签。

## 描述

`SuspendEnum` 是一个字符串枚举，定义了对应于 `ChatObject` 生命周期中关键执行点的内置断点标签。这些标准标签无需使用自定义字符串字面量即可实现对执行流程的精确控制。

## 枚举值

### `MEMORY`

- **值**: `"ChatObject::memory_limiting"`
- **描述**: 在内存摘要前触发，当上下文超出token限制时
- **用途**: 在自动摘要前检查或修改上下文的理想选择

### `SINGLE_TOOL`

- **值**: `"ChatObject::single_tool_call"`
- **描述**: 在Agent执行期间每次单独的工具调用前触发
- **用途**: 调试工具交互、验证工具参数或实现自定义工具审批逻辑的理想选择

### `PRECOMPLE`

- **值**: `"matcher_call::pre_completion"`
- **描述**: 在向LLM发送消息进行完成前触发
- **用途**: 用于最终消息验证、安全检查或在模型推理前修改上下文

### `COMPLE`

- **값**: `"matcher_call::post_completion"`
- **描述**: 在接收模型响应后但在处理之前触发
- **用途**: 响应验证、内容过滤或实现自定义响应处理逻辑的绝佳选择

## 使用示例

```python
from amrita_core import ChatObject, SuspendEnum
from amrita_core.types import MemoryModel, Message

async def main():
    context = MemoryModel()
    train = Message(content="You are a helpful assistant.", role="system")

    chat = ChatObject(
        context=context,
        session_id="session_123",
        user_input="What's the weather like?",
        train=train.model_dump()
    )

    # 사용标准断점의 외부 컨트롤러
    async def controller(chat_obj):
        # 대기 도구 호출 중단점
        await chat_obj.io_stream.wait_to_suspend(SuspendEnum.SINGLE_TOOL.value)
        print("도구 호출 예정입니다!")

        # 복구하고 완료 중단점 대기
        chat_obj.io_stream.resume()
        await chat_obj.io_stream.wait_to_suspend(SuspendEnum.COMPLE.value)
        print("모델 응답을 받았습니다!")
        chat_obj.io_stream.resume()

    controller_task = asyncio.create_task(controller(chat))

    try:
        async with chat.begin():
            async for response in chat.io_stream.get_response_generator():
                print(response, end="", flush=True)
    finally:
        controller_task.cancel()
```

## 최적의 방법

- **표준 태그 사용**: 사용자 정의 문자열 태그 대신 `SuspendEnum` 값을 우선적으로 사용하여 유지 관리성을 높입니다.
- **버전 호환성**: 표준 태그는 버전 간 일관성을 보장합니다.
- **디버깅**: 여러 표준 중단점을 결합하여 포괄적인 디버깅 워크플로를 구현합니다.
- **보안**: `PRECOMPLE` 중단점을 사용하여 모델 호출 전 최종 보안 검증을 수행합니다.

## 관련 문서

- [挂기 및 복구 메커니즘](../../concepts/suspend.md)
- [ChatObject 클래스](ChatObject.md)
