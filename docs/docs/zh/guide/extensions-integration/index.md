# 扩展与集成

## 扩展机制

### 简单工具

AmritaCore 提供了通过简单工具扩展功能的简便方式：

```python
from amrita_core import simple_tool

@simple_tool
def add(a: int, b: int) -> int:
    """将两个数字相加

    Args:
        a (int): 第一个数字
        b (int): 第二个数字

    Returns:
        int: a 和 b 的和
    """
    return a + b
```

此工具将自动注册并对 agent 可用。

在工具的 `__doc__` 块中，你可以按 Google 格式添加工具的描述和参数。当工具被调用时，这些参数将用于向 LLM 描述参数。

**注册范围**：使用 `@simple_tool` 注册的工具在模块加载期间添加到全局容器中，对所有会话可用。

**支持的类型**：`@simple_tool` 装饰器支持丰富的类型注解，包括 Pydantic 模型、List[T] 和 Optional[T]。完整的类型支持详情请参见[工具系统](../concepts/tool.md)文档。

### 工具系统扩展

AmritaCore 提供了通过自定义工具扩展其功能的灵活方式。你可以创建 agent 可用于执行特定任务的新工具：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

# 首先定义具有高级验证的函数 schema
calculate_math_tool = FunctionDefinitionSchema(
    name="calculate_math",
    description="计算数学表达式的结果",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "expression": FunctionPropertySchema(
                type="string",
                description="要计算的数学表达式",
                minLength=1,
                maxLength=1000,
                pattern=r"^[0-9+\-*/().\s]+$"
            ),
            "precision": FunctionPropertySchema(
                type="integer",
                description="结果的小数位数",
                minimum=0,
                maximum=10,
                default=2
            )
        },
        required=["expression"]
    )
)

@on_tools(data=calculate_math_tool)
async def calculate_math(data: dict) -> str:
    """计算数学表达式的结果"""
    expression = data["expression"]
    precision = data.get("precision", 2)
    try:
        result = eval(expression)
    except Exception as e:
        return f"计算错误：{e}"
```

**注册范围**：与 `@simple_tool` 一样，`@on_tools` 装饰器在模块加载期间将工具注册到全局容器。

### 增强的校验功能

`FunctionPropertySchema` 支持全面的 JSON Schema 校验，具有特定类型的约束：

- **数字约束**：`minimum`、`maximum`、`exclusiveMinimum`、`exclusiveMaximum`、`multipleOf`
- **字符串约束**：`minLength`、`maxLength`、`pattern`、`format`
- **数组约束**：`items`、`minItems`、`maxItems`、`uniqueItems`
- **对象约束**：`properties`、`required`、`additionalProperties`
- **特殊值**：`enum`、`const`、`default`
- **联合类型**：`type` 可以是允许类型的列表（仅手动 schema 定义可用，不适用于 `@simple_tool`）

这些约束在 LLM 生成工具调用时自动校验，确保只有有效的参数值被传递给工具函数。

> **关于注册方式**：
>
> - **装饰器**（`@simple_tool`、`@on_tools`）：在模块加载时注册到全局容器，对所有会话可用
> - **直接管理器操作**：允许在运行时使用 `ToolsManager` 或 `MultiToolsManager` 实例进行特定会话的工具管理

### 高级工具模式

对于需要访问事件上下文或更高级处理的工具，可以使用 `custom_run` 模式：

````python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema, ToolContext
from amrita_core.logging import logger

# 定义函数 schema
process_message_tool = FunctionDefinitionSchema(
    name="processing_message",
    description="向用户描述 agent 当前正在做什么，表达 agent 的内部思考",
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
    """处理消息并通过 chat object 发送给用户"""
    content = ctx.data["content"]
    logger.debug(f"[LLM-ProcessMessage] {content}")

    # 直接通过 chat object 发送消息
    await ctx.ctx.chat_object.yield_response(f"{content}\n")

    # 返回处理结果
    return f"已向用户发送消息：\n\n```text\n{content}\n```\n"
````

在自定义运行模式中：

- 函数接收 [ToolContext](../api-reference/classes/ToolContext.md) 对象而非原始参数
- [ToolContext](../api-reference/classes/ToolContext.md) 包含：
  - `ctx.data`：传递给工具的参数
  - `ctx.ctx`：包含当前执行上下文的 [StrategyContext](../api-reference/classes/StrategyContext.md)，包括对 chat object 的访问
- 函数可以是同步或异步的
- 返回类型可以是 `str` 或 `None`

### 事件钩子扩展

事件钩子允许你拦截和修改处理管道：

```python
from amrita_core.hook.event import PreCompletionEvent, CompletionEvent
from amrita_core.hook.on import on_precompletion, on_completion
from amrita_core.types import Message

@on_precompletion().handle()
async def inject_context(event: PreCompletionEvent):
    """在 LLM 处理前注入自定义上下文"""
    event.messages.append(Message(
        role="system",
        content="请记住在回复中保持简洁和有帮助。"
    ))


@on_completion().handle()
async def log_response(event: CompletionEvent):
    """处理后记录响应"""
    print(f"收到响应：{event.response[:100]}...")
```

### 协议适配器与自定义分词器

协议适配器允许 AmritaCore 与不同的 LLM 提供商或通信协议配合使用。分词器处理文本分词以用于记忆管理和上下文窗口。

适配器和分词器都支持**两种注册机制**：

#### 机制 1：通过子类化隐式注册（任意位置）

在代码库中的任意位置子类化 `ModelAdapter` 或 `BaseTokenizer` — 当模块被导入时，`__init_subclass__` 钩子会自动将类注册到对应的管理器（`AdapterManager` 或 `TokenizerManager`）中。

```python
# my_project/adapters.py
from amrita_core.base.adapter import ModelAdapter
from amrita_core.base.tokenizer import BaseTokenizer

class MyCustomAdapter(ModelAdapter):
    # 手动导入此模块以触发注册
    ...

class MyCustomTokenizer(BaseTokenizer):
    # 手动导入此模块以触发注册
    ...
```

然后显式导入以触发注册：

```python
import my_project.adapters  # 触发 __init_subclass__ 注册
```

#### 机制 2：命名空间包自动发现（推荐用于内置风格）

AmritaCore 使用 Python 的**命名空间包**机制（PEP 420）在启动时自动发现适配器和分词器。只需将文件放在 `adapters/` 或 `tokenizers/` 目录中，**不带 `__init__.py`** — 该目录变为命名空间包，`side_effect_import`（在 `amrita_core` 导入期间调用）会自动发现并导入所有子模块。

```
src/amrita_core/
├── adapters/          # ← 必须没有 __init__.py
│   ├── openai.py      # 自动发现
│   ├── anthropic.py   # 自动发现
│   └── my_adapter.py  # ← 你的自定义适配器
├── tokenizers/        # ← 必须没有 __init__.py
│   ├── simple.py      # 自动发现
│   └── my_tokenizer.py # ← 你的自定义分词器
```

**关键规则**：`adapters/` 和 `tokenizers/` 目录**不能包含 `__init__.py`**。`__init__.py` 会将其变为常规包，破坏命名空间包自动发现机制。

#### 示例：创建适配器

```python
# src/amrita_core/adapters/custom_protocol.py
from amrita_core.base.adapter import ModelAdapter
from amrita_core.types import ModelPreset
from collections.abc import AsyncGenerator, Iterable
from amrita_core.types import UniResponse

class CustomAdapter(ModelAdapter):
    def __init__(self, preset: ModelPreset):
        super().__init__(preset=preset)
        self.__override__ = True  # 允许覆盖现有适配器

    async def call_api(
        self, messages: Iterable
    ) -> AsyncGenerator[str | UniResponse[str, None], None]:
        # 逐个产出响应块，最后产出 UniResponse
        yield "响应块"
        yield UniResponse(
            role="assistant",
            content="完整响应",
            usage=None,
            tool_calls=None,
        )

    @staticmethod
    def get_adapter_protocol() -> str | tuple[str, ...]:
        return "custom_protocol"
```

## MCP 客户端集成

### 什么是 MCP？

模型上下文协议（MCP）是将工具和数据源连接到 AI 模型的标准。它允许模型以结构化的方式与外部系统交互，扩展其能力超越训练数据。

### mcp.ClientManager MCP 客户端管理

[ClientManager](../api-reference/classes/ClientManager.md) 类管理 MCP 客户端连接：

```python
from amrita_core.tools import mcp

# 为会话初始化 MCP 客户端
async def setup_mcp_clients():
    client_manager = mcp.ClientManager()
    scripts = [
        "/path/to/script1.mcp",
        "/path/to/script2.mcp"
    ]
    await client_manager.initialize_scripts_all(scripts)
```

### MCP 脚本配置

在设置中配置 MCP 脚本：

```python
from amrita_core.config import AmritaConfig, FunctionConfig

config = AmritaConfig(
    function_config=FunctionConfig(
        agent_mcp_client_enable=True,
        agent_mcp_server_scripts=[
            "./mcp-scripts/weather.mcp",
            "./mcp-scripts/database.mcp",
            "./mcp-scripts/calendar.mcp"
        ]
    )
)
```

### MCP 实际示例

真实世界的 MCP 用例：

1. **数据库访问**：通过 MCP 客户端查询数据库
2. **文件系统操作**：安全地读写文件
3. **API 集成**：连接第三方 API
4. **IoT 设备**：与物理设备交互

关于 MCP 服务器集成的详细信息、架构以及如何创建自己的 MCP 服务器，请参见 [MCP 服务器集成](./mcp-server-integration.md)。

## 自定义扩展开发

### 创建自定义工具

为特定功能开发自定义工具：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema
import json

# 定义翻译的函数 schema
translate_tool = FunctionDefinitionSchema(
    name="translate_text",
    description="将文本翻译为目标语言",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "text": FunctionPropertySchema(
                type="string",
                description="要翻译的文本"
            ),
            "target_language": FunctionPropertySchema(
                type="string",
                description="目标语言代码（默认：en）",
                default="en"
            )
        },
        required=["text"]
    )
)

@on_tools(data=translate_tool)
async def translate_text(data: dict) -> str:
    """将文本翻译为目标语言"""
    text = data["text"]
    target_language = data.get("target_language", "en")
    simulated_translation = f"[翻译为 {target_language.upper()}]：{text}"
    return simulated_translation

# 定义获取公司信息的函数 schema
company_info_tool = FunctionDefinitionSchema(
    name="get_company_info",
    description="获取公司信息",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "company_name": FunctionPropertySchema(
                type="string",
                description="要查询的公司名称"
            )
        },
        required=["company_name"]
    )
)

@on_tools(data=company_info_tool)
async def get_company_info(data: dict) -> str:
    """获取公司信息"""
    company_name = data["company_name"]
    result = {
        "name": company_name,
        "status": "模拟",
        "info": f"关于 {company_name} 的信息"
    }
    return json.dumps(result)
```

### 创建自定义事件处理器

构建用于专门处理的自定义事件处理器：

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion
from amrita_core.types import Message

@on_precompletion().handle()
async def security_check(event: PreCompletionEvent):
    """在处理前执行安全检查"""
    for msg in event.messages:
        if msg.role == "user":
            if "harmful" in msg.content.lower():
                event.messages.append(Message(
                    role="system",
                    content="内容已进行安全过滤"
                ))
```

### 创建自定义协议适配器

为不同的 LLM 提供商构建适配器。参见[协议适配器与自定义分词器](#协议适配器与自定义分词器)了解两种注册机制。

```python
from amrita_core.base.adapter import ModelAdapter
from amrita_core.types import ModelPreset, UniResponse
from collections.abc import AsyncGenerator, Iterable
import aiohttp

class CustomLLMAdapter(ModelAdapter):
    def __init__(self, preset: ModelPreset):
        super().__init__(preset=preset)
        self.__override__ = True

    async def call_api(
        self, messages: Iterable
    ) -> AsyncGenerator[str | UniResponse[str, None], None]:
        headers = {
            'Authorization': f'Bearer {self.preset.api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'messages': list(messages),
            'model': self.preset.model,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.preset.base_url}/chat/completions",
                                   json=payload, headers=headers) as response:
                result = await response.json()
                content = result['choices'][0]['message']['content']
                yield content
                yield UniResponse(
                    role="assistant",
                    content=content,
                    usage=result.get('usage', {}),
                    tool_calls=None,
                )

    @staticmethod
    def get_adapter_protocol() -> str | tuple[str, ...]:
        return "custom_llm_protocol"
```

### 包命名约定与发布

为保持生态系统一致性，向 PyPI 发布 AmritaCore 扩展时使用以下命名前缀：

| 扩展类型      | 包名前缀             | 示例                         |
| ------------- | -------------------- | ---------------------------- |
| **适配器**    | `amcore-adapter-*`   | `amcore-adapter-grok`        |
| **分词器**    | `amcore-tokenizer-*` | `amcore-tokenizer-bert`      |
| **策略**      | `amcore-strategy-*`  | `amcore-strategy-reflection` |
| **钩子/事件** | `amcore-hook-*`      | `amcore-hook-rate-limiter`   |
| **工具**      | `amcore-tool-*`      | `amcore-tool-calculator`     |

发布和分享扩展的步骤：

1. 按照上述命名约定打包为单独的 Python 模块
2. 在 `pyproject.toml` 中添加相关分类器，如 `Framework :: AmritaCore`
3. 记录功能、使用示例和依赖项
4. 发布到 PyPI 或托管在 Git 仓库中

## 第三方集成

### 常见 LLM 提供商集成

与各种 LLM 提供商集成：

```python
# OpenAI 兼容端点
from amrita_core.types import ModelPreset, ModelConfig

openai_preset = ModelPreset(
    model="gpt-4",
    base_url="https://api.openai.com/v1",
    api_key="your-openai-api-key",
    config=ModelConfig(stream=True)
)

# Azure OpenAI
azure_preset = ModelPreset(
    model="your-deployment-name",
    base_url="https://your-resource.openai.azure.com",
    api_key="your-azure-api-key",
    config=ModelConfig(stream=True)
)
```

### 数据库连接

使用工具连接数据库：

```python
import sqlite3
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

query_db_tool = FunctionDefinitionSchema(
    name="query_database",
    description="查询 SQLite 数据库",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "query": FunctionPropertySchema(
                type="string",
                description="要执行的 SQL 查询"
            )
        },
        required=["query"]
    )
)

@on_tools(data=query_db_tool)
async def query_database(data: dict) -> str:
    """查询 SQLite 数据库"""
    query = data["query"]
    try:
        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return str(results)
    except Exception as e:
        return f"执行查询时出错：{str(e)}"
```

### API 集成

与外部 API 集成：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema
import aiohttp

get_weather_tool = FunctionDefinitionSchema(
    name="get_weather_data",
    description="从外部 API 获取天气数据",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "city": FunctionPropertySchema(
                type="string",
                description="要获取天气的城市"
            )
        },
        required=["city"]
    )
)

@on_tools(data=get_weather_tool)
async def get_weather_data(data: dict) -> str:
    """从外部 API 获取天气数据"""
    city = data["city"]
    api_key = "your-weather-api-key"
    url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return f"{city} 天气：{data['current']['condition']['text']}，{data['current']['temp_c']}°C"
            else:
                return f"无法获取 {city} 的天气信息"
```

### 与其他框架集成

将 AmritaCore 与其他框架组合使用：

```python
# 示例：与 FastAPI 集成构建 Web 服务
from fastapi import FastAPI
from amrita_core import ChatObject, minimal_init
from amrita_core.config import AmritaConfig, set_config

app = FastAPI()

@app.on_event("startup")
async def startup():
    await minimal_init(AmritaConfig())

@app.post("/chat/")
async def chat_endpoint(user_input: str, session_id: str):
    from amrita_core.base.backend import BackendSlots
    from amrita_core.builtins.backends import LegacyBackend

    chat = ChatObject(
        train={"role": "system", "content": "你是一个有帮助的助手。"},
        user_input=user_input,
        context=None,
        session_id=session_id,
        backend=BackendSlots(ability=LegacyBackend(), memory=LegacyBackend()),
    )

    async with chat.begin():
        response = await chat.full_response()
        await chat  # 等待任务完成再退出

    return {"response": response}
```
