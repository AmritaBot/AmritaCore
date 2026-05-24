# 功能实现

## 4.1 初始化和加载

### 4.1.1 init() 初始化函数

`init()` 函数初始化AmritaCore的核心组件，在执行任何其他操作之前必须调用：

```python
from amrita_core import init

# 初始化AmritaCore
init()
```

此函数执行几项关键任务：

- 设置内部日志记录
- 初始化Jieba进行文本处理（如果可用）
- 加载内置模块
- 准备核心框架以供使用

### 4.1.2 load_amrita() 异步加载

`load_amrita()` 函数异步加载AmritaCore组件，特别是当启用了MCP客户端功能时：

```python
import asyncio
from amrita_core import load_amrita

async def main():
    # 加载AmritaCore组件
    await load_amrita()

asyncio.run(main())
```

### 4.1.3 配置设置和检索

#### 4.1.3.1 set_config() 设置配置

`set_config()` 函数将配置应用到AmritaCore：

```python
from amrita_core.config import AmritaConfig, set_config

# 创建并设置配置
config = AmritaConfig()
set_config(config)
```

## 4.2 Agent策略生命周期方法

AmritaCore中的Agent策略实现了几个在执行过程中不同点被调用的生命周期方法。

### 4.2.1 on_post_process() 后处理钩子

`on_post_process()` 方法是一个**执行后钩子**，在所有Agent步骤成功完成后调用。此钩子对**所有策略类别**（`"agent"`、`"rag"`、`"workflow"`、`"agent-mixed"`）都可用。

**目的**: 此钩子允许策略在生成最终响应之前执行最终上下文修改、添加完成指令或执行清理操作。

**使用示例**:

```python
async def on_post_process(self) -> None:
"""在成功Agent执行后调用"""
if self.call_count >= 2: # 仅在实际调用了工具时
self.ctx.message.append(
Message(
role="user",
content="<END_OF_PROCESS>\n请根据我们之前获得的信息直接回答我。\n</END_OF_PROCESS>"
)
)

```

**关键特性**:

- 仅在成功执行时调用（未发生异常）
- 对**所有策略类别**都可用
- 可以在最终完成之前修改对话上下文
- 适用于添加最终指令或上下文摘要

### 4.2.2 其他生命周期方法

- **`run()`**: `"workflow"` 和 `"rag"` 类别的主要执行方法
- **`single_execute()`**: `"agent"` 和 `"agent-mixed"` 类别的单步执行方法
- **`on_exception(exc: BaseException)`**: 在执行过程中发生异常时调用。默认实现不再抛出 `NoExceptionHandler` 异常，而是静默通过（pass）。自定义策略应重写此方法以实现特定的错误处理逻辑。

#### 异常处理最佳实践

```python
from amrita_core.agent.strategy import AgentStrategy

class CustomAgentStrategy(AgentStrategy):
    async def on_exception(self, exc: BaseException) -> None:
        """自定义异常处理逻辑"""
        # 记录异常
        logger.error(f"Agent执行失败: {exc}")

        # 可选择性地重新抛出特定异常
        if isinstance(exc, ValueError):
            raise exc

        # 或者优雅地处理并继续
        self.ctx.message.append(
            Message(
                role="user",
                content="处理过程中发生错误。请重试。"
            )
        )
```

**重要说明**：

- 默认行为现在是**静默失败处理** - 异常被捕获但不会重新抛出
- 自定义策略应在 `on_exception()` 中实现自己的错误处理逻辑
- 如果需要旧的行为（重新抛出异常），在自定义实现中显式调用 `raise exc`
- 此更改提高了生产环境中优雅错误处理的健壮性

## 4.2 对话交互流程

### 4.2.1 创建 ChatObject 对话对象

`ChatObject` 类是对话的主要接口：

```python
from amrita_core import ChatObject
from amrita_core.types import MemoryModel, Message

# 创建记忆上下文
context = MemoryModel()

# 创建系统消息
train = Message(content="您是一个有用的助手。", role="system")

# 创建 ChatObject
chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="你好，你怎么样？",
    train=train.model_dump()
)
```

### 4.2.2 begin() 执行对话

#### 基本用法

`begin()` 方法执行对话并处理输入：

```python
# 执行对话
await chat.begin()
...
# 使用上下文管理器
async with chat.begin() as chat:...

```

#### 用作上下文管理器（推荐）

```python

# 我们更推荐使用上下文管理器：
async with chat.begin():
    ...

```

### 4.2.3 full_response() 获取完整响应

`full_response()` 方法从对话中检索完整响应：

```python
# 获取完整响应
response = await chat.full_response()
print(response)
```

### 4.2.4 流式响应处理

AmritaCore使用**AnyIO内存对象流**进行流式响应，提供内置的背压处理：

```python
# 处理流式响应
async for message in chat.get_response_generator():
    content = message if isinstance(message, str) else message.get_content()
    print(content, end="")
```

**背压机制变更**：

- 使用带自动背压的单个AnyIO内存对象流

现在 `_put_to_queue()` 方法使用AnyIO的 `send()` 方法并带有超时：

```python
await asyncio.wait_for(self._send_stream.send(item), timeout=self._q_tout)
```

当缓冲区满时，生产者会自动等待直到有空间可用，消除了对复杂溢出逻辑的需求。

### 4.2.5 响应回调

AmritaCore支持响应回调以实现实时交互：

```python
async def response_callback(message):
    print(message)

chat.set_callback_func(response_callback)
await chat.begin()
```

::: warning

`get_response_generator()` 或 `full_response()` 是一次性操作。这意味着您只能调用 `full_response()` 或 `get_response_generator()` 一次，否则将引发 `RuntimeError`。

:::

### 4.2.5 对话生命周期

典型的对话生命周期包括：

1. 创建记忆上下文
2. 定义系统指令
3. 创建 ChatObject
4. 执行对话
5. 处理响应
6. 更新上下文以进行后续交互

```python
# 完整对话生命周期
context = MemoryModel()
train = Message(content="你是一个乐于助人的助手。", role="system")

async with ChatObject(
    context=context,
    session_id="session_123",
    user_input="你好！",
    train=train.model_dump()
).begin() as chat:
    async for message in chat.get_response_generator():
        print(message, end="")

# 更新上下文以进行下次交互
context = chat.data
```

## 4.3 事件处理实现

### 4.3.1 @on_event 事件监听器

使用 `@on_event` 装饰器创建事件监听器：

```python
from amrita_core.hook.on import on_event

@on_event()
def my_event_handler(event):
    print(f"收到事件: {event}")

```

### 4.3.2 @on_precompletion 预完成钩子

预完成钩子在发送请求到 LLM 之前执行：

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion().handle()
async def preprocess_request(event: PreCompletionEvent):
    # 在发送到 LLM 之前修改消息
    event.messages.append(Message(role="system", content="请在回复中保持简洁"))

```

### 4.3.3 @on_completion 后完成钩子

后完成钩子在从 LLM 接收响应后执行：

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion().handle()
async def postprocess_response(event: CompletionEvent):
    # 在返回给用户之前处理响应
    print(f"收到响应: {event.response[:50]}...")

```

### 4.3.4 事件处理最佳实践

- 在 LLM 处理之前使用预完成钩子修改消息
- 使用后完成钩子处理或记录响应
- 在执行异步操作时确保事件处理器是异步的
- 从处理器返回事件对象以继续链

## 4.4 工具调用实现

### 4.4.1 工具注册示例

为Agent注册具有全面验证的工具：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# 使用高级验证定义函数模式
weather_func = FunctionDefinitionSchema(
    name="get_current_weather",
    description="获取给定位置的当前天气",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "location": FunctionPropertySchema(
                type="string",
                description="城市和州，例如 旧金山，CA",
                minLength=2,           # 最小位置长度
                maxLength=100,         # 最大合理长度
                pattern=r"^[a-zA-Z\s,-]+$"  # 仅允许字母、空格、逗号、连字符
            ),
            "unit": FunctionPropertySchema(
                type="string",
                enum=["celsius", "fahrenheit"],
                description="温度单位"
            ),
            "forecast_days": FunctionPropertySchema(
                type="integer",
                description="预测天数（0表示仅当前天气）",
                minimum=0,
                maximum=7,
                default=0
            )
        },
        required=["location"]
    )
)

@on_tools(data=weather_func)
async def get_current_weather(data: dict) -> str:
    """
    获取给定位置的当前天气
    """
    location = data["location"]
    unit = data.get("unit", "celsius")  # 如果未提供，默认为摄氏度
    forecast_days = data.get("forecast_days", 0)

    # 模拟带验证的天气查询
    if forecast_days == 0:
        return f"{location}的当前天气是晴朗的，温度是22度{unit}。"
    else:
        return f"{location}的天气预报（{forecast_days}天）：晴朗，温度范围18-25度{unit}。"
```

### 增强的验证功能

`FunctionPropertySchema` 支持全面的 JSON Schema 验证：

- **数值约束**：`minimum`、`maximum`、`exclusiveMinimum`、`exclusiveMaximum`、`multipleOf`
- **字符串约束**：`minLength`、`maxLength`、`pattern`、`format`
- **数组约束**：`items`、`minItems`、`maxItems`、`uniqueItems`
- **对象约束**：`properties`、`required`、`additionalProperties`
- **特殊值**：`enum`、`const`、`default`
- **联合类型**：`type` 可以是允许类型的列表

当 LLM 生成工具调用时，这些约束会自动验证，确保只有有效的参数值传递给您的工具函数。

### 4.4.2 工具执行流程

工具执行流程包括：

1. 在 LLM 响应中检测工具
2. 参数提取
3. 工具执行
4. 结果整合到对话中

### 4.4.3 错误处理

工具实现中的适当错误处理：

```python
from typing import Any
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# 定义函数模式
divide_func = FunctionDefinitionSchema(
    name="safe_divide",
    description="安全地除两个数",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "dividend": FunctionPropertySchema(
                type="number",
                description="除法中的被除数"
            ),
            "divisor": FunctionPropertySchema(
                type="number",
                description="除法中的除数"
            )
        },
        required=["dividend", "divisor"]
    )
)

@on_tools(data=divide_func)
async def safe_divide(data: dict) -> str:
    """
    安全地除两个数
    """
    try:
        dividend = data["dividend"]
        divisor = data["divisor"]

        if divisor == 0:
            return "错误：不能除以零"

        result = dividend / divisor
        return f"{dividend} 除以 {divisor} 等于 {result}"
    except Exception as e:
        return f"发生错误：{str(e)}"
```

### 4.4.4 自定义运行模式

某些工具可能需要访问事件上下文或需要更高级的处理。为此，可以启用 `custom_run` 选项：

````python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema, ToolContext
from amrita_core.logging import logger

# 定义函数模式
process_message_tool = FunctionDefinitionSchema(
    name="processing_message",
    description="描述Agent当前正在做什么，并向用户表达Agent的内部想法",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "content": FunctionPropertySchema(
                type="string",
                description="描述当前操作的消息内容"
            )
        },
        required=["content"]
    )
)

@on_tools(data=process_message_tool, custom_run=True)
async def process_message(ctx: ToolContext) -> str | None:
    """
    处理消息并通过聊天对象发送给用户
    """
    content = ctx.data["content"]
    logger.debug(f"[LLM-ProcessMessage] {content}")

    # 直接向聊天对象发送消息
    await ctx.ctx.chat_object.yield_response(f"{content}\n")

    # 返回处理结果
    return f"向用户发送了消息:\n\n```text\n{content}\n```\n"
````

在自定义运行模式中：

- 函数接收 `ToolContext` 对象而不是原始参数
- `ToolContext` 包含：
  - `ctx.data`: 传递给工具的参数
  - `ctx.ctx`: 包含当前执行上下文的 [StrategyContext](../api-reference/classes/StrategyContext.md)，包括对聊天对象的访问
- 函数可以是同步或异步的
- 返回类型可以是 `str` 或 `None`

## 4.5 记忆管理

### 4.5.1 MemoryModel 记忆结构

`MemoryModel` 类结构：

```python
from amrita_core.types import MemoryModel, Message

# 创建和使用记忆模型
memory = MemoryModel()
memory.messages.append(Message(role="user", content="你好"))
memory.messages.append(Message(role="assistant", content="你好！"))
```

### 4.5.2 上下文窗口管理

使用配置管理上下文窗口：

```python
from amrita_core.config import LLMConfig

# 限制记忆中的消息数量
llm_config = LLMConfig(
    memory_length_limit=50  # 只保留最后 50 条消息
)
```

### 4.5.3 消息摘要功能

自动消息摘要：

```python
from amrita_core.config import LLMConfig

# 启用记忆摘要
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # 在上下文长度达到限制时进行摘要的消息占比
)
```

### 4.5.4 长对话处理

高效处理长对话：

```python
from amrita_core.config import FunctionConfig, LLMConfig, AmritaConfig

# 长对话的配置
long_convo_config = AmritaConfig(
    function_config=FunctionConfig(
        use_minimal_context=True  # 使用最小上下文以节省Token
    ),
    llm=LLMConfig(
        enable_memory_abstract=True,  # 启用摘要
        memory_length_limit=100       # 增加记忆限制
    )
)
```

### 4.5.5 记忆优化技术

- 在适当时候使用最小上下文
- 为长时间运行的会话启用记忆摘要
- 实施会话清理策略
- 定期监控Token使用情况

## 4.6 日志和调试

### 4.6.1 Logger 日志系统

使用内置日志记录器：

```python
from amrita_core.logging import logger

# 记录信息消息
logger.info("开始对话...")

# 记录调试信息
logger.debug("处理消息: %s", user_input)

# 记录错误
logger.error("处理请求失败: %s", error)
```

### 4.6.2 get_last_response() 获取最后响应

从对话生成器中检索最后的响应。此函数支持在提取最终响应的同时将中间块流式传输到目标流。

```python
from amrita_core.libchat import get_last_response
from amrita_core.streaming import SuspendObjectStream

# 基本用法 - 仅获取最后的响应
last_resp = await get_last_response(chat_object)

# 高级用法 - 在获取最后响应的同时流式传输中间块
class ResponseStream(SuspendObjectStream[str]):
    pass

response_stream = ResponseStream()
last_resp = await get_last_response(
    chat_object,
    yield_to=response_stream,
    yield_to_wrapper=lambda chunk: f"[STREAMING] {chunk}"
)
```

**函数签名**:

```python
async def get_last_response(
    generator: AsyncGenerator[RESPONSE_TYPE | UniResponse[str, None], None],
    yield_to: SuspendObjectStream[RESPONSE_TYPE] | None = None,
    yield_to_wrapper: Callable[[RESPONSE_TYPE], RESPONSE_TYPE] | None = None,
) -> UniResponse[str, None]
```

**参数**:

- `generator`: 异步生成器，产生响应部分（字符串、MessageContent 或 UniResponse 对象）
- `yield_to` (可选): 发送中间块的目标流。如果提供，所有非 UniResponse 块将被发送到此流。
- `yield_to_wrapper` (可选): 在将块发送到目标流之前转换块的函数。

**返回值**:

- 生成器中的最后一个 `UniResponse` 对象

**异常**:

- `RuntimeError`: 如果生成器中未找到响应

**使用场景**:

1. **基本响应提取**: 当您只需要最终响应元数据（使用情况、工具调用等）时
2. **带最终响应的流式传输**: 当您想要将中间内容流式传输给用户，同时捕获最终响应进行处理时
3. **响应转换**: 当您需要转换流式内容时（例如，添加前缀、格式化、过滤）

**与 ChatObject 的示例**:

```python
from amrita_core import ChatObject
from amrita_core.libchat import get_last_response

# 创建聊天对象
chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="天气怎么样？",
    train=train.model_dump()
)

# 在捕获最终响应的同时流式传输响应
async with chat.begin():
    final_response = await get_last_response(
        chat.get_response_generator(),
        yield_to=your_websocket_stream,
        yield_to_wrapper=lambda chunk: {"type": "stream", "content": str(chunk)}
    )

    # 现在您既有流式内容，也有最终响应元数据
    print(f"使用的总Token数: {final_response.usage.total_tokens}")
    print(f"执行的工具调用次数: {len(final_response.tool_calls or [])}")
```

### 4.6.3 调试技巧

- 在开发期间启用调试日志
- 监控Token使用情况以防止超出限制
- 使用流式响应进行实时反馈
- 为健壮的应用程序实现适当的错误处理
