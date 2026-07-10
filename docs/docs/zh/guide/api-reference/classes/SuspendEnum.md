# SuspendEnum

> **v0.12.0 迁移**: `SuspendEnum` 和 `BuiltinName` 已从 `amrita_core.chatmanager.enums` 移至 `amrita_core.enums`。旧模块已标记为 `DeprecationWarning`，将在 v0.13.x 移除。

`SuspendEnum` 类为 AmritaCore 中的挂起/恢复机制提供标准化的断点标签。

## 描述

`SuspendEnum` 是一个字符串枚举，定义了对应于 `ChatObject` 生命周期中关键执行点的内置断点标签。这些标准标签无需使用自定义字符串字面量即可实现对执行流程的精确控制。

## 枚举值

### `LOAD_STATE`

- **值**: `"ChatObject::load_state"`
- **描述**: 从后端加载运行时状态时触发
- **用途**: 在执行开始时发生，用于从配置的 BackendSlots 加载记忆和能力上下文。适用于调试状态加载或实现自定义状态初始化

### `ENTRY_POINT`

- **值**: `"ChatObject::_entry"`
- **描述**: 在 ChatObject 执行的最开始时触发
- **用途**: 在主工作流开始之前，用于执行前设置、日志记录或初始化挂钩

### `TRAIN_RENDER`

- **值**: `"ChatObject::render_train_template"`
- **描述**: 渲染 Jinja2 训练/提示模板时触发
- **用途**: 检查或修改渲染后的系统提示的理想选择

### `MEMORY`

- **值**: `"ChatObject::memory_limiting"`
- **描述**: 在内存摘要前触发，当上下文超出 token 限制时
- **用途**: 在自动摘要前检查或修改上下文的理想选择

### `MESSAGES_PREPARED`

- **值**: `"ChatObject::prepare_send_messages"`
- **描述**: 消息列表准备完成后、运行预完成匹配器之前触发
- **用途**: 最终消息验证或最后一刻修改的绝佳时机

### `PRECOMPLE`

- **值**: `"matcher_call::pre_completion"`
- **描述**: 在向 LLM 发送消息进行完成前触发
- **用途**: 用于最终消息验证、安全检查或在模型推理前修改上下文

### `STRATEGY_START`

- **值**: `"ChatObject::run_strategy_start"`
- **描述**: Agent 策略执行开始时触发
- **用途**: 策略级别的 instrumentation 或自定义策略前逻辑的理想选择

### `LLM_CALL`

- **值**: `"ChatObject::call_llm"`
- **描述**: 实际 LLM API 调用期间触发
- **用途**: 监控 API 延迟或在模型推理周围注入行为

### `SINGLE_TOOL`

- **值**: `"ChatObject::single_tool_call"`
- **描述**: 在 Agent 执行期间每次单独的工具调用前触发
- **用途**: 调试工具交互、验证工具参数或实现自定义工具审批逻辑的理想选择

### `COMPLE`

- **值**: `"matcher_call::post_completion"`
- **描述**: 在接收模型响应后但在处理之前触发
- **用途**: 响应验证、内容过滤或实现自定义响应处理逻辑的绝佳选择

### `MEMORY_APPEND`

- **值**: `"Component::memory_append"`
- **描述**: 将 LLM 响应附加到上下文消息包装器时触发
- **用途**: 由 [`APPEND_RESPONSE`](../api-reference/classes/APPEND_RESPONSE.md) 组件节点暴露。在 LLM 完成后发生，用于将模型的响应添加为助手消息。

### `APPLY_CONTEXT`

- **值**: `"Component::apply_context"`
- **描述**: 将最终上下文包装器写回记忆模型时触发
- **用途**: 由 [`APPLY_CONTEXT`](../api-reference/classes/APPLY_CONTEXT.md) 组件节点暴露。在记忆提交前发生，用于将更新后的消息列表写入 `MemoryModel.messages`。

### `COMMIT_MEMORY`

- **值**: `"ChatObject::commit_memory"`
- **描述**: 执行流水线完成后，记忆提交回后端时触发
- **用途**: 在工作流结束时发生，用于持久化对话状态。适用于监控持久化或实现自定义记忆提交逻辑

### `FINALIZE`

- **值**: `"ChatObject::finalize"`
- **描述**: 在 ChatObject 执行流水线结束时触发
- **用途**: 清理、记录最终状态或后处理

## BuiltinName

`BuiltinName` 是一个伴随枚举，为内部框架组件提供别名。当前定义：

### `AGENT_STRATEGY`

- **值**: `"ChatObject::__agent_main__"`
- **描述**: 工作流引擎使用的 Agent 策略子程序内部别名

## 使用示例

```python
from amrita_core import ChatObject, SuspendEnum
from amrita_core.types import Message

async def main():
    train = Message(content="You are a helpful assistant.", role="system")

    chat = ChatObject(
        train=train.model_dump(),
        user_input="What's the weather like?",
        session_id="session_123",
    )

    # 使用标准断点的外部控制器
    async def controller(chat_obj):
        # 等待工具调用断点
        await chat_obj.io_stream.wait_to_suspend(SuspendEnum.SINGLE_TOOL.value)
        print("即将进行工具调用！")

        # 恢复并等待完成断点
        chat_obj.io_stream.resume()
        await chat_obj.io_stream.wait_to_suspend(SuspendEnum.COMPLE.value)
        print("已收到模型响应！")
        chat_obj.io_stream.resume()

    controller_task = asyncio.create_task(controller(chat))

    try:
        async with chat.begin():
            async for response in chat.io_stream.get_response_generator():
                print(response, end="", flush=True)
    finally:
        controller_task.cancel()
```

## 最佳实践

- **使用标准标签**：优先使用 `SuspendEnum` 值而不是自定义字符串标签，以提高可维护性
- **版本兼容性**：标准标签确保跨版本的一致性
- **调试**：组合多个标准断点以实现全面的调试工作流
- **安全**：使用 `PRECOMPLE` 断点在模型调用前执行最终安全验证

## 相关文档

- [挂起与恢复机制](../../concepts/suspend.md)
- [ChatObject 类](ChatObject.md)
