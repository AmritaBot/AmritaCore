# API 参考

本参考按功能模块组织。每个条目链接到类页面以获取完整文档。

## 核心 API 函数

### `load_amrita()`

`load_amrita()` 函数在配置中启用 MCP 时异步加载 MCP 客户端。适配器在导入时已注册——`load_amrita()` 不会加载它们。

```python
import asyncio
from amrita_core import load_amrita


async def main():
    await load_amrita()


asyncio.run(main())
```

**使用说明**：

- 自 v0.9.0rc1 起不再需要先调用 `init()`
- 如果使用自定义配置，应在 `set_config()` 之后调用
- 启用 MCP 时，必须调用 `load_amrita()`

### `minimal_init()`

`minimal_init()` 函数执行最小初始化：应用配置并在启用时加载 MCP 客户端。适配器在导入时已注册。

```python
from amrita_core import minimal_init

await minimal_init()
```

### `set_config(config)`

`set_config()` 函数将配置应用到 AmritaCore。

```python
from amrita_core.config import AmritaConfig, set_config

config = AmritaConfig()
set_config(config)
```

**参数**：

- `config` ([AmritaConfig](classes/AmritaConfig.md))：要设置的配置对象

**使用说明**：

- 应在 `load_amrita()` 之前调用

### `get_config()`

`get_config()` 函数检索当前的 AmritaCore 配置。

```python
from amrita_core.config import get_config

config = get_config()
print(config.function_config.use_minimal_context)
```

**返回**：[AmritaConfig](classes/AmritaConfig.md) - 当前配置对象

**使用说明**：

- 若 AmritaCore 尚未初始化，会抛出 `RuntimeError`

### `create_agent()`

`create_agent()` 工厂函数通过自动创建临时预设来创建 agent。**这是构建 agent 的推荐入口点。**

```python
from amrita_core import create_agent

agent = create_agent(
    "https://api.example.com",  # 替换为你的 API 地址
    "your-api-key",  # 替换为你的 API 密钥
    model="gpt-4",  # 替换为你想要的模型
    model_config={"temperature": 0.7},
)
```

**参数**：

- `base_url` (str)：API 端点 URL
- `api_key` (str)：API 密钥
- `model` (str，可选)：要使用的模型。默认为 `"auto"`
- `train` (str | None，可选)：系统提示词；默认为内置指令
- `model_config` (`ModelConfig` | dict | None，可选)：可选的模型配置。默认为 None
- `config` ([AmritaConfig](classes/AmritaConfig.md) | None，可选)：agent 的配置。默认为全局配置
- `**kwargs`：转发给 [AgentRuntime](classes/AgentRuntime.md) 的额外参数（如 `strategy`、`template`、`session_id`、`backend`）

**返回**：[AgentRuntime](classes/AgentRuntime.md) - 配置好的 agent 运行时实例

**使用说明**：

- 函数自动创建临时预设；持久化预设请用 [PresetManager](classes/PresetManager.md)
- 返回的 agent 可通过 `get_chatobject()` 复用多次交互
- `create_agent()` **没有 `protocol` 参数**——它总是构造默认协议
  （`"__main__"`，即 OpenAI 兼容适配器）的预设。供应商由
  `base_url` + `model` 决定；DeepSeek、Azure 或任意 OpenAI 兼容端点都走
  同一适配器。要使用 Anthropic 线上格式，请构造 `protocol="anthropic"`
  的 `ModelPreset` 并直接传给 `AgentRuntime`——见
  [模型适配器](../extensions-integration/adapters.md)

## 配置

| 类                                                  | 描述                                                     |
| --------------------------------------------------- | -------------------------------------------------------- |
| [AmritaConfig](classes/AmritaConfig.md)             | 中央配置对象（function_config / llm / cookie / builtin） |
| [FunctionConfig](classes/FunctionConfig.md)         | 功能行为：上下文、工具调用上限、参数校验、MCP 客户端     |
| [LLMConfig](classes/LLMConfig.md)                   | LLM 行为：token 限制、重试、回退、历史压缩               |
| [BuiltinAgentConfig](classes/BuiltinAgentConfig.md) | 内置 agent 策略：工具调用模式、思考模式、停滞检测        |
| [ReactConfig](classes/ReactConfig.md)               | ReAct 推理增强：结构化推理、反思、工具预测               |

## 聊天管理

| 类                                          | 描述                         |
| ------------------------------------------- | ---------------------------- |
| [ChatObject](classes/ChatObject.md)         | 单次对话的核心类             |
| [ChatManager](classes/ChatManager.md)       | 管理运行中的 ChatObject 实例 |
| [ChatObjectMeta](classes/ChatObjectMeta.md) | ChatObject 快照的元数据模型  |
| [SuspendEnum](classes/SuspendEnum.md)       | 挂起/恢复机制的标准断点标签  |

## 类型

| 类                                            | 描述                               |
| --------------------------------------------- | ---------------------------------- |
| [Message](classes/Message.md)                 | 对话中的单条消息                   |
| [SendMessageWrap](classes/SendMessageWrap.md) | 发送给模型的消息列表的可迭代包装器 |
| [MemoryModel](classes/MemoryModel.md)         | 存储对话历史                       |
| [ModelPreset](classes/ModelPreset.md)         | 特定模型的完整配置                 |
| [ThinkingConfig](classes/ThinkingConfig.md)   | 思考/推理配置                      |
| [EmbeddingChunk](classes/EmbeddingChunk.md)   | 嵌入适配器返回的嵌入向量           |

## 工具

| 类                                                              | 描述                                           |
| --------------------------------------------------------------- | ---------------------------------------------- |
| [FunctionDefinitionSchema](classes/FunctionDefinitionSchema.md) | 函数定义模式（name、description、parameters）  |
| [ToolFunctionSchema](classes/ToolFunctionSchema.md)             | 完整的函数调用模式（function + type + strict） |
| [ToolData](classes/ToolData.md)                                 | 注册工具的数据模型（元数据 + 实现）            |
| [ToolContext](classes/ToolContext.md)                           | 工具函数执行期间传入的上下文                   |
| [MultiToolsManager](classes/MultiToolsManager.md)               | 支持启停的多实例工具注册表                     |
| [MCPClient](classes/MCPClient.md)                               | 用于连接 MCP 服务器的 MCP 客户端               |
| [ClientManager](classes/ClientManager.md)                       | 管理单个 MCP 客户端                            |
| [MultiClientManager](classes/MultiClientManager.md)             | 管理多个 MCP 客户端                            |

这些模型背后的 schema 层位于 `amrita_core.tools.schema`。它有两条正交的轴：投影（projection）把 Python 变成模式，编译（compilation）把模式变回用于校验调用的验证器：

| 函数                                                 | 方向 | 用途                                     |
| ---------------------------------------------------- | ---- | ---------------------------------------- |
| `function_definition_from_pydantic(model, ...)`      | 投影 | 从单个 Pydantic 模型得到完整工具定义     |
| `function_definition_from_signature(func, ...)`      | 投影 | 从可调用对象的签名得到定义               |
| `python_type_to_property_schema(t, ns, desc)`        | 投影 | 把单个 Python 类型转为单个属性模式       |
| `pydantic_model_to_property_schema(model, ns, desc)` | 投影 | 把单个 Pydantic 模型转为 object 属性模式 |
| `compile_parameters_model(params)`                   | 编译 | 把参数模式转为 Pydantic 验证器           |
| `validate_arguments(params, args)`                   | 编译 | 校验一次调用并返回实际使用的参数         |

参见[工具系统（概念）](../concepts/tool.md#schemas-and-validation)。

## 后端与上下文

| 类                                                  | 描述                                         |
| --------------------------------------------------- | -------------------------------------------- |
| [BackendSlots](classes/BackendSlots.md)             | 打包 ability、memory 与 billing 后端以供 I/O |
| [AbilityBackend](classes/AbilityBackend.md)         | 加载工具、MCP 客户端与预设的抽象基类         |
| [MemoryBackend](classes/MemoryBackend.md)           | 加载与提交记忆的抽象基类                     |
| [BillingBackend](classes/BillingBackend.md)         | 逐请求计费记录的可选接收端                   |
| [NullBillingBackend](classes/NullBillingBackend.md) | 空操作计费接收端；记录只留在内存中           |
| [LegacyBackend](classes/LegacyBackend.md)           | 默认的进程内后端实现                         |
| [AbilityContext](classes/AbilityContext.md)         | 运行时能力状态（工具、预设、MCP 客户端）     |
| [SessionUsageProxy](classes/SessionUsageProxy.md)   | 运行级计费台账，带可选的外部接收端           |
| [DatabackendOptions](classes/DatabackendOptions.md) | 细粒度控制后端拉取/提交操作                  |

## 历史压缩

| 类                                                      | 描述                                 |
| ------------------------------------------------------- | ------------------------------------ |
| [ContextCompactor](classes/ContextCompactor.md)         | 压缩策略：单个模型的触发、摘要与折叠 |
| [ContextOverflowError](classes/ContextOverflowError.md) | 供应商因超出窗口而拒绝请求时抛出     |

## Agent 策略

| 类                                                          | 描述                                     |
| ----------------------------------------------------------- | ---------------------------------------- |
| [AgentRuntime](classes/AgentRuntime.md)                     | `create_agent()` 返回的 agent 运行时包装 |
| [AgentStrategy](classes/AgentStrategy.md)                   | agent 策略的抽象基类                     |
| [StrategyContext](classes/StrategyContext.md)               | 传给策略执行的上下文                     |
| [BaseReActAgentStrategy](classes/BaseReActAgentStrategy.md) | ReAct 策略的基础实现                     |
| [ReActAgentStrategy](classes/ReActAgentStrategy.md)         | 标准 ReAct 策略                          |
| [NoActionAgentStrategy](classes/NoActionAgentStrategy.md)   | 不执行任何动作的策略                     |

## 事件与钩子

| 类                                                  | 描述                                                                                                                                  |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| [CompletionEvent](classes/CompletionEvent.md)       | 模型完成后触发（事件类型 `COMPLETION`）                                                                                               |
| [PreCompletionEvent](classes/PreCompletionEvent.md) | 策略运行与完成之前触发（`BEFORE_COMPLETION`）                                                                                         |
| [FallbackContext](classes/FallbackContext.md)       | 预设回退事件的基础上下文（`PRESET_FALLBACK`）；子类有 `CompletionFallbackContext`、`ToolsFallbackContext`、`EmbeddingFallbackContext` |

## 预设与适配器

| 类                                                  | 描述                     |
| --------------------------------------------------- | ------------------------ |
| [PresetManager](classes/PresetManager.md)           | 管理模型预设             |
| [MultiPresetManager](classes/MultiPresetManager.md) | 支持测试的多实例预设管理 |
| [ModelAdapter](classes/ModelAdapter.md)             | 模型适配器的抽象基类     |

## 计费

| 类                                          | 描述                                 |
| ------------------------------------------- | ------------------------------------ |
| [RateConfig](classes/RateConfig.md)         | 附在模型预设上的单价快照             |
| [BillingRecord](classes/BillingRecord.md)   | 单次供应商请求的用量与计价快照       |
| [BillingBackend](classes/BillingBackend.md) | 把计费记录镜像到外部存储的可选接收端 |

## 装饰器

### `@simple_tool`

`@simple_tool` 装饰器用于注册简单工具。

```python
from amrita_core import simple_tool


@simple_tool
def add(a: int, b: int) -> int:
    """Add number

    Args:
        a (int): First number
        b (int): Second number
    """
    return a + b
```

**用途**：注册一个简单工具，从类型标注与 docstring 自动推断模式。

**支持的参数类型**：

- 基本类型：`str`、`int`、`float`、`bool`
- 字面量类型：`Literal["a", "b"]` → 自动生成 `string` + `enum` 约束；`Literal[1, 2, 3]` 同样支持 `integer` 枚举
- 用于复杂嵌套结构的 Pydantic BaseModel 类
- 容器类型：`List[T]`（仅支持单层）
- 可选类型：`Optional[T]` 或 `T | None`

**不支持的类型**（会抛出 ValueError）：

- Dict 类型（请改用 Pydantic 模型）
- 嵌套容器（如 `List[List[str]]`）
- 多类型联合（如 `str | int`）
- `Any` 或 `object` 类型

**注册行为**：

- 工具在模块加载期间注册到**全局容器**
- 注册发生在会话创建之前，因此对所有会话可用
- 若需要按会话管理工具，请直接使用 `MultiToolsManager` 的操作

**使用说明**：

- 工具以函数名注册
- 每个参数的描述来自函数的 docstring（Google 风格）
- 函数的所有参数都必须有类型标注（不允许无类型参数）

### `@on_tools`

`@on_tools` 装饰器把函数注册为 agent 可调用的工具。

```python
from typing import Any

from amrita_core import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

DEFINITION = FunctionDefinitionSchema(
    name="Add number",
    description="Add two numbers",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "a": FunctionPropertySchema(type="number", description="The first number"),
            "b": FunctionPropertySchema(type="number", description="The second number"),
        },
        required=["a", "b"],
    ),
)


@on_tools(DEFINITION)
async def add(data: dict[str, Any]) -> str:
    """Add two numbers"""
    return str(data["a"] + data["b"])
```

**用途**：把函数注册为 agent 可调用的工具，并对工具模式拥有细粒度控制。

**注册行为**：

- 与 `@simple_tool` 一样，在模块加载期间注册到**全局容器**
- 可显式控制工具模式的定义
- 若更希望从 Pydantic 模型推导模式，请用 [`function_definition_from_pydantic`](#工具)

**使用说明**：

- 处理函数接收参数 `dict`（当 `custom_run=True` 时接收 `ToolContext`）；参数在运行前会按模式校验
- **不会**使用函数 docstring，`description` 来自你传入的定义

### `@on_event`

`@on_event` 装饰器把函数注册为事件处理函数。

```python
from amrita_core.hook.on import on_event


@on_event().handle()
def my_event_handler(event):
    # Handle custom events
    pass
```

**用途**：注册函数以处理处理流水线中的特定事件。

> 每个匹配器工厂（`on_event`、`on_precompletion`、`on_completion`、
> `on_preset_fallback`）返回的都是 `Matcher`，因此必须用 `.handle()` 挂接处理器
> ——单独写 `@on_event("<type>")` 会抛出 `TypeError`。

### `@on_precompletion`

`@on_precompletion` 装饰器注册在完成请求发送给 LLM 之前运行的函数。

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion


@on_precompletion().handle()
async def preprocess_request(event: PreCompletionEvent):
    # Modify the messages before sending to LLM
    print(event)
```

**用途**：在请求发送给 LLM 之前运行，可修改消息或做其他预处理。

### `@on_completion`

`@on_completion` 装饰器注册在收到 LLM 完成结果之后运行的函数。

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion


@on_completion().handle()
async def postprocess_response(event: CompletionEvent):
    # Process the response after receiving from LLM
    print(event)
```

**用途**：在收到 LLM 响应之后运行，可对响应做后处理。

## 类型定义

### 预定义类型

AmritaCore 提供了若干预定义类型以保持一致性：

- `EmbeddingChunk`：表示嵌入适配器返回的嵌入向量
- [FunctionDefinitionSchema](classes/FunctionDefinitionSchema.md)：函数参数的模式
- [MemoryModel](classes/MemoryModel.md)：存储对话历史
- [ModelPreset](classes/ModelPreset.md)：特定模型的完整配置
- [ChatManager](classes/ChatManager.md)：管理运行中的 ChatObject 实例
- [ChatObjectMeta](classes/ChatObjectMeta.md)：ChatObject 快照的元数据模型
- [SuspendEnum](classes/SuspendEnum.md)：挂起/恢复机制的标准断点标签
- [ToolContext](classes/ToolContext.md)：为工具执行提供上下文

### Step 循环类型（内置 ReAct）

- [AgentRunState](classes/AgentRunState.md)：语义级 step 运行状态（计划、停滞窗口、token）
- [DAGNode](classes/DAGNode.md)：任务计划的子步骤
- [StepLifecycleEvents](classes/StepLifecycleEvents.md)：可变 step 生命周期事件（`step_intro` / `step_leave` / `step_iteration` / `tool_call` / `tool_return`）与 `StepAbortError`

完整机制见[进阶 → Step 循环](../advanced/step-loop.md)。

### 异常类型

AmritaCore 可能抛出以下异常：

- `RuntimeError`：在初始化之前访问配置时抛出
- `ValueError`：向函数提供非法值时抛出
- `TypeError`：向函数传入类型错误的值时抛出

### 类型检查

AmritaCore 大量使用 Pydantic 模型做类型校验。编写自定义组件时，请确保类型标注正确：

```python
from typing import Optional
from amrita_core.types import BaseModel


class CustomConfig(BaseModel):
    param1: str
    param2: Optional[int] = None
    param3: list[str] = []
```

本 API 参考对 AmritaCore 的核心接口、类与装饰器做了完整概览。各组件协同工作，为构建 AI agent 提供灵活而强大的框架。
