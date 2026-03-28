# 挂起与恢复机制

**注意：这是一个用于特殊场景的高级功能。大多数用户不需要直接使用它。**

AmritaCore 提供了一套简单显式的挂起机制，允许外部控制 `ChatObject` 的执行流程，在指定节点暂停和恢复处理。适用场景：

- 需要在处理步骤之间检查状态的交互式调试
- 在复杂多代理系统中实现自定义流程控制
- 与需要同步卡点的外部系统协同工作

## 工作原理

`ChatObject` 的核心生命周期方法（`_entry`、`_run`、`_run_strategy` 等）均被 `@suspend` 装饰器托管，执行前会自动检测挂起信号。

基础使用步骤：

1. 从 `ChatObject` 执行上下文**外部**，单独异步任务中调用 `await chat.wait_to_suspend(timeout)` 监听挂起状态
2. `ChatObject` 运行到下一个被 `@suspend` 装饰的方法时自动暂停
3. 调用 `await chat.resume()` 恢复正常执行流程

## 手动使用 `_wait_for_continue()`

如需更细粒度控制，可在自定义异步逻辑中手动调用 `await chat._wait_for_continue()`，自由植入自定义挂起点：

```python
import asyncio
from amrita_core import create_agent, minimal_init

async def custom_processing_step(chat_obj):
    """带有手动挂起点的自定义处理函数"""
    print("开始处理步骤...")
    await asyncio.sleep(0.5)

    # 手动挂起点：仅外部触发 wait_to_suspend 时阻塞，否则立即返回
    await chat_obj._wait_for_continue()

    print("在挂起点后继续...")
    await asyncio.sleep(0.5)

async def main():
    await minimal_init()
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-3.5-turbo",
    )

    chat = agent.get_chatobject("Hello!")

    # 外部独立控制任务
    async def external_controller(chat_obj):
        await chat_obj.wait_to_suspend(timeout=5.0)
        print("聊天已挂起！")
        await asyncio.sleep(1)
        await chat_obj.resume()
        print("聊天已恢复！")

    controller_task = asyncio.create_task(external_controller(chat))

    try:
        await custom_processing_step(chat)
        async with chat.begin():
            async for response in chat.get_response_generator():
                content = response if isinstance(response, str) else response.get_content()
                print(content, end="", flush=True)
    finally:
        controller_task.cancel()

asyncio.run(main())
```

### 关键说明

- `_wait_for_continue()` 会被所有 `@suspend` 装饰的方法自动调用
- 支持开发者手动植入，定制业务内部挂点
- 无待处理挂起请求时，调用会立即返回，不阻塞流程
- 基于异步信号实现，独立于业务执行流

## 使用模式示例

```python
import asyncio
from amrita_core import create_agent, minimal_init

async def main():
    await minimal_init()
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-3.5-turbo",
    )

    chat = agent.get_chatobject("Hello!")

    # 外部并发控制逻辑
    async def external_controller(chat_obj):
        await chat_obj.wait_to_suspend(timeout=5.0)
        print("聊天已挂起，可以在此检查状态")
        # 可执行状态查看、上下文修改、外部联动等自定义逻辑
        await chat_obj.resume()

    async with chat.begin():
        controller_task = asyncio.create_task(external_controller(chat))
        try:
            async for response in chat.get_response_generator():
                content = response if isinstance(response, str) else response.get_content()
                print(content, end="", flush=True)
        finally:
            controller_task.cancel()

asyncio.run(main())
```

## 重要使用说明

- 控制接口必须在 `ChatObject` 主异步上下文之外、独立并发任务中调用
- `wait_to_suspend` 超时参数用于避免无限阻塞
- 属于底层能力，面向框架扩展、高级调试与定制流程编排场景

## 何时不使用此功能

普通业务开发请优先使用标准交互模式：

- 流式响应输出：`async with chat.begin(): async for response in chat.get_response_generator()`
- 回调式响应：`chat.set_callback_func(callback)` + `await chat.begin()`
- 完整一次性应答：`async with chat.begin(): response = await chat.full_response()`

仅在需要外部精细控制内部执行流程的高阶场景，才启用挂起/恢复能力。
