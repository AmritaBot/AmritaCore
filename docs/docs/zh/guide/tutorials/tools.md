# 2. 给 Agent 添加工具

## 本章目标

让 agent 调用你写的函数。学完你能：

- 用 `@simple_tool` 把 Python 函数暴露给模型
- 用 `@on_tools` 精确控制调用契约

## 概念速览（用到才讲）

- **工具**：带 JSON Schema 的函数。模型**从不执行**你的函数——它只生成调用
  请求；框架校验参数、运行函数、把结果喂回。

## 1. 用 `@simple_tool` 定义简单工具

最快的方式——类型与 docstring 自动转为 JSON Schema：

```python
from amrita_core import simple_tool


@simple_tool
def add(a: int, b: int) -> int:
    """Add two numbers

    Args:
        a (int): First number
        b (int): Second number

    Returns:
        int: Sum of a and b
    """
    return a + b
```

`@simple_tool` 读取 Google 风格 docstring 构建 schema。支持的注解包括
Pydantic 模型、`list[T]`、`Optional[T]` 与标量类型。

## 2. 在 Agent 中使用工具

```python
import asyncio
import os

from amrita_core import create_agent, minimal_init


async def main() -> None:
    await minimal_init()
    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key=os.environ["OPENAI_API_KEY"],
        model="gpt-4o-mini",
    )
    chat = agent.get_chatobject("What is 123 + 456? Use the add tool.")
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)


asyncio.run(main())
```

agent **自行决定**何时调用 `add`；框架按 schema 校验参数并把结果回喂。

## 3. 用 `@on_tools` 完全控制

需要精确控制 schema（校验约束、描述、枚举值）时手动定义：

```python
from amrita_core import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

WEATHER_DEFINITION = FunctionDefinitionSchema(
    name="get_weather",
    description="Get the current weather for a city",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "city": FunctionPropertySchema(
                type="string",
                description="City name, e.g. 'Paris'",
                minLength=1,
            ),
            "unit": FunctionPropertySchema(
                type="string",
                enum=["celsius", "fahrenheit"],
                description="Temperature unit",
            ),
        },
        required=["city"],
    ),
)


@on_tools(WEATHER_DEFINITION)
async def get_weather(data: dict[str, str]) -> str:
    city = data["city"]
    unit = data.get("unit", "celsius")
    return f"Weather in {city}: 22°{unit[0].upper()}"
```

handler 接收校验后的参数 `dict`，**必须返回字符串**（它成为模型看到的
工具结果）。

需要框架访问（流式、上下文）的工具请用 `custom_run` 模式——
见[工具系统](../concepts/tool.md)。

## 刚才发生了什么

- `@simple_tool`：schema 来自类型注解 + docstring，零样板
- `@on_tools`：显式 JSON Schema 与校验约束
- 两者都在模块加载时全局注册；结果流回模型

## 下一步

[3. 流式与回调](streaming.md)——读取流，包括结构化元数据。
