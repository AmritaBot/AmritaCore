# 挂起与恢复机制

**注意：这是一个用于特殊场景的高级功能。大多数用户不需要直接使用它。**

AmritaCore 提供了一套简单显式的挂起机制，允许外部控制 `ChatObject` 的执行流程，在指定节点暂停和恢复处理。此机制通过 `SuspendObjectStream` 基类实现，`ChatObject` 继承自该基类。

适用场景：

- 需要在处理步骤之间检查状态的交互式调试
- 在复杂多代理系统中实现自定义流程控制
- 与需要同步卡点的外部系统协同工作
- **带标签的断点控制**：通过 tag 标记特定断点，实现精确的流程控制

## 标准断点标签

AmritaCore 通过 `SuspendEnum` 枚举提供了**标准化的断点标签**。这些内置标签对应 ChatObject 生命周期中的关键执行点：

```python
from amrita_core import SuspendEnum

# 可用的标准断点标签：
SuspendEnum.MEMORY        # "ChatObject::memory_limiting" - 内存摘要前
SuspendEnum.SINGLE_TOOL   # "ChatObject::single_tool_call" - 每次工具调用前
SuspendEnum.PRECOMPLE     # "matcher_call::pre_completion" - 模型完成前
SuspendEnum.COMPLE        # "matcher_call::post_completion" - 模型完成后
```

**推荐**：使用这些标准标签而不是自定义字符串标签，以获得更好的可维护性和兼容性。

## 工作原理

`ChatObject` 的核心生命周期方法（`_entry`、`_run`、`_run_strategy` 等）均被 `@SuspendObjectStream.suspend` 装饰器托管，执行前会自动检测挂起信号。

基础使用步骤：

1. 从 `ChatObject` 执行上下文**外部**，单独异步任务中调用 `await chat.wait_to_suspend(timeout)` 监听挂起状态
2. `ChatObject` 运行到下一个被 `@SuspendObjectStream.suspend` 装饰的方法时自动暂停
3. 调用 `chat.resume()` 恢复正常执行流程

## 使用 Tag 标记断点

AmritaCore 支持使用 tag 参数为挂起点添加唯一标识，实现精确的断点控制：

### 使用标准标签的基本用法

```python
from amrita_core import ChatObject, SuspendEnum
from amrita_core.types import MemoryModel, Message

context = MemoryModel()
train = Message(content="You are a helpful assistant.", role="system")

chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump()
)

# 外部控制器监听特定的标准断点
async def external_controller(chat_obj):
    # 等待标准的 "single_tool_call" 断点
    await chat_obj.wait_to_suspend(SuspendEnum.SINGLE_TOOL.value, timeout=5.0)
    print("在工具调用前挂起！")

    # 可以在此检查或修改状态
    # ...

    chat_obj.resume()

# 启动控制器任务
controller_task = asyncio.create_task(external_controller(chat))
```

### 在自定义函数中使用标签

使用 `@SuspendObjectStream.suspend_with_tag` 装饰器为自定义函数添加带标签的挂起点：

```python
from amrita_core.streaming import SuspendObjectStream

class MyAgent:
    @SuspendObjectStream.suspend_with_tag("before_api_call")
    async def call_external_api(self, chat_obj: ChatObject, url: str):
        """在调用外部API前挂起（如果外部监听器正在等待此标签）"""
        # 如果外部调用了 wait_to_suspend("before_api_call")
        # 代码将在此处暂停，直到调用 resume()
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

    @SuspendObjectStream.suspend_with_tag("after_response")
    async def post_process_response(self, chat_obj: ChatObject, response: str):
        """在处理响应后挂起"""
        # 后处理逻辑
        print(f"处理响应: {response}")
```

### 标签匹配规则

1. **精确匹配**：`wait_to_suspend("xxx")` 只会匹配 `@SuspendObjectStream.suspend_with_tag("xxx")` 装饰的函数
2. **无标签挂起**：`wait_to_suspend()` 会匹配所有被 `@SuspendObjectStream.suspend` 装饰的函数
3. **优先级**：带标签的挂起优先于无标签的挂起

```python
# 示例：多断点控制流程
async def multi_breakpoint_controller(chat_obj):
    # 等待第一个断点
    await chat_obj.wait_to_suspend("step1")
    print("步骤1完成")

    # 继续等待第二个断点
    await chat_obj.wait_to_suspend("step2")
    print("步骤2完成")

    # 最后等待任意断点
    await chat_obj.wait_to_suspend()  # 匹配任何被 suspend 装饰的方法
    print("任意步骤完成")

    chat_obj.resume()
```

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
        chat_obj.resume()
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

- `_wait_for_continue()` 会被所有 `@SuspendObjectStream.suspend` 装饰的方法自动调用
- 支持开发者手动植入，定制业务内部挂点
- 无待处理挂起请求时，调用会立即返回，不阻塞流程
- 基于异步信号实现，独立于业务执行流
- **tag 参数传递**：手动调用时可传入 tag 参数 `await chat_obj._wait_for_continue(tag="custom_tag")`

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
        print("聊天已挂起。")
        await asyncio.sleep(1)
        chat_obj.resume()
        print("聊天已恢复。")

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
- **tag 参数帮助精确定位**：在复杂流程中使用 tag 可以准确控制特定断点
- 属于底层能力，面向框架扩展、高级调试与定制流程编排场景
- **继承关系**：由于 `ChatObject` 继承自 `SuspendObjectStream`，所有挂起/恢复方法都可在 ChatObject 实例上使用

## 何时不使用此功能

普通业务开发请优先使用标准交互模式：

- 流式响应输出：`async with chat.begin(): async for response in chat.get_response_generator()`
- 回调式响应：`chat.set_callback_func(callback)` + `await chat.begin()`
- 完整一次性应答：`async with chat.begin(): response = await chat.full_response()`

仅在需要外部精细控制内部执行流程的高阶场景，才启用挂起/恢复能力。
