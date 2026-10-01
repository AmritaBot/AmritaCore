# SuspendEnum

> **v0.12.0 迁移**：`SuspendEnum` 已从 `amrita_core.chatmanager.enums` 移至 `amrita_core.enums`。

`SuspendEnum` 类为 AmritaCore 中的挂起/恢复机制提供标准化的断点标签。

## 说明

`SuspendEnum` 是字符串枚举，定义了与 `ChatObject` 生命周期中关键执行点一一对应的内置断点标签。使用这些标准标签可以精确控制执行流程，无需自定义字符串字面量。

## 枚举值

### `LOAD_STATE`

- **值**：`"ChatObject::load_state"`
- **描述**：从后端加载运行时状态时触发
- **用途**：在执行开始时从 `BackendSlots` 加载记忆与能力上下文。适合调试状态加载或实现自定义状态初始化

### `ENTRY_POINT`

- **值**：`"ChatObject::_entry"`
- **描述**：ChatObject 执行开始时触发
- **用途**：适合执行前的准备工作、日志记录，或主工作流启动前的初始化钩子

### `TRAIN_RENDER`

- **值**：`"ChatObject::render_train_template"`
- **描述**：渲染 Jinja2 训练/提示词模板时触发
- **用途**：适合检查或修改渲染后的系统提示词

### `MEMORY`

- **值**：`"ChatObject::memory_limiting"`
- **描述**：记忆变更挂起点
- **用途**：被**两个**节点拦截。`COMPACT` 在把历史前缀折叠进 `MemoryModel.abstract` 时挂起；`APPEND_RESPONSE` 在追加助手回复之后、写回之前挂起。值字符串仍保留压缩器取代限流器之前的旧名 `memory_limiting`

### `MESSAGES_PREPARED`

- **值**：`"ChatObject::prepare_send_messages"`
- **描述**：消息列表准备完成但运行预完成匹配器之前触发
- **用途**：适合做最终的消息校验或临时修改

### `PRECOMPLE`

- **值**：`"matcher_call::pre_completion"`
- **描述**：发送消息给 LLM 完成之前触发
- **用途**：适合在模型推理前做最终消息校验、安全检查或上下文修改

### `STRATEGY_START`

- **值**：`"ChatObject::run_strategy_start"`
- **描述**：agent 策略执行开始时触发
- **用途**：适合策略层埋点或自定义策略前置逻辑

### `LLM_CALL`

- **值**：`"ChatObject::call_llm"`
- **描述**：实际 LLM API 调用期间触发
- **用途**：适合监控 API 延迟，或在模型推理前后注入行为

### `SINGLE_TOOL`

- **值**：`"ChatObject::single_tool_call"`
- **描述**：agent 执行期间每次单独工具调用之前触发
- **用途**：适合调试工具交互、校验工具参数，或实现自定义的工具审批逻辑

### `COMPLE`

- **值**：`"matcher_call::post_completion"`
- **描述**：收到模型回复之后、处理之前触发
- **用途**：适合回复校验、内容过滤，或实现自定义的回复处理逻辑

### `MEMORY_APPEND`

- **值**：`"Component::memory_append"`
- **描述**：把 LLM 回复追加到上下文消息包装时触发
- **用途**：由 `APPEND_RESPONSE` 组件节点暴露。发生在 LLM 完成之后，用于把模型回复作为助手消息加入。

### `APPLY_CONTEXT`

- **值**：`"Component::apply_context"`
- **描述**：把最终上下文包装写回记忆模型时触发
- **用途**：由 `APPLY_CONTEXT` 组件节点暴露。发生在记忆提交之前，用于把更新后的消息列表写入 `MemoryModel.messages`。

### `COMMIT_MEMORY`

- **值**：`"ChatObject::commit_memory"`
- **描述**：执行流水线完成后、记忆提交回后端时触发
- **用途**：发生在工作流最末端，用于持久化会话状态。适合监控持久化过程或实现自定义记忆提交逻辑

### `FINALIZE`

- **值**：`"ChatObject::finalize"`
- **描述**：ChatObject 执行流水线结束时触发
- **用途**：适合清理、记录最终状态或后处理

### `ADVANCE_COUNTER`

- **值**：`"ChatObject::advance_counter"`
- **描述**：agent 调用计数器自增时触发
- **用途**：在自增之后拦截，因此处理函数看到的是自增后的值。适合审计一次运行消耗了多少轮工具调用

## Step 循环边界标记

以下两个值由内置 Step 循环发出，每个 Step 各一次。`ReActAgentStrategy.intro_step` / `leave_step` 正是挂接在这里（见 [Step 循环](../../advanced/step-loop.md)）。

### `STEP_INTRO`

- **值**：`"ChatObject::step_intro"`
- **描述**：进入 Step 边界
- **用途**：下一个 plan 节点成为当前 Step 的位置，也是重置 Step 级状态的位置

### `STEP_LEAVE`

- **值**：`"ChatObject::step_leave"`
- **描述**：离开 Step 边界
- **用途**：已完成 Step 在此汇总，并在此评估 Step 之间的压缩

> `SuspendEnum.CALL_SINGLE_STRATEGY` 已定义但未挂接到任何节点——策略块不再通过挂起标签进入。

## 使用示例

```python
import asyncio

from amrita_core import ChatObject, SuspendEnum
from amrita_core.types import Message


async def main():
    train = Message(content="You are a helpful assistant.", role="system")

    chat = ChatObject(
        session_id="session_123",
        user_input="What's the weather like?",
        train=train.model_dump(),
    )

    # 外部控制器使用标准断点
    async def controller(chat_obj):
        # 等待工具调用断点
        await chat_obj.io_stream.wait_to_suspend(SuspendEnum.SINGLE_TOOL.value)
        print("About to call a tool!")

        # 恢复并等待完成断点
        chat_obj.io_stream.resume()
        await chat_obj.io_stream.wait_to_suspend(SuspendEnum.COMPLE.value)
        print("Received model response!")
        chat_obj.io_stream.resume()

    controller_task = asyncio.create_task(controller(chat))

    try:
        async with chat.begin():
            async for response in chat.io_stream.get_response_generator():
                print(response, end="", flush=True)
            await chat  # 退出前等待任务完成
    finally:
        controller_task.cancel()
```

## 最佳实践

- **使用标准标签**：优先使用 `SuspendEnum` 值而非自定义字符串标签，便于维护
- **版本兼容**：标准标签保证跨版本稳定
- **调试**：组合多个标准断点以构建完整的调试工作流
- **安全**：在模型调用前使用 `PRECOMPLE` 断点做最终安全校验

## 相关文档

- [挂起与恢复机制](../../advanced/suspend.md)
- [ChatObject 类](ChatObject.md)

