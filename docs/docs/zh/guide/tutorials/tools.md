# 为 Agent 添加工具

工具让你的智能体能够调用你定义的函数——查询数据库、计算数值、获取网页等等。在本教程中，你将使用 [`@simple_tool`](../api-reference/index.md#simple_tool) 和 [`@on_tools`](../api-reference/index.md#on_tools) 注册工具，然后让你的智能体使用它们。

## 1. 使用 `@simple_tool` 创建简单工具

[`@simple_tool`](../api-reference/index.md#simple_tool) 装饰器将函数注册为工具，并根据其类型注解和 Google 风格文档字符串自动推断 schema：

```python
from amrita_core import simple_tool


@simple_tool
def add(a: int, b: int) -> int:
    """两个数相加。

    Args:
        a: 第一个数。
        b: 第二个数。
    """
    return a + b
```

支持的参数类型有 `str`、`int`、`float`、`bool`、`Literal[...]`、Pydantic 模型、单层 `list[T]` 和 `Optional[T]`。不支持的类型（如字典、嵌套容器、多类型联合）在注册时会引发 `ValueError`。

## 2. 在 Agent 中使用工具

`@simple_tool` 注册到**全局容器**，因此你的智能体会自动获取它：

```python
import asyncio

from amrita_core import create_agent, minimal_init, simple_tool


@simple_tool
def add(a: int, b: int) -> int:
    """两个数相加。

    Args:
        a: 第一个数。
        b: 第二个数。
    """
    return a + b


async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        train="你是一个可以使用工具的有帮助的助手。",
    )

    chat = agent.get_chatobject("1234 + 5678 等于多少？")
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat  # 等待任务完成——退出会取消它
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
```

默认的 [ReAct 策略](../concepts/agent-strategy.md) 将决定何时调用工具并将结果反馈回对话。

## 3. 使用 `@on_tools` 获得完全控制

当你需要对工具 schema 进行精确控制（参数描述、必填字段）时，使用 [`@on_tools`](../api-reference/index.md#on_tools) 并搭配显式的 [FunctionDefinitionSchema](../api-reference/classes/FunctionDefinitionSchema.md)：

```python
from typing import Any

from amrita_core import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

DEFINITION = FunctionDefinitionSchema(
    name="add",
    description="两个数相加",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "a": FunctionPropertySchema(type="number", description="第一个数"),
            "b": FunctionPropertySchema(type="number", description="第二个数"),
        },
        required=["a", "b"],
    ),
)


@on_tools(DEFINITION)
async def add(data: dict[str, Any]) -> str:
    """两个数相加"""
    return str(data["a"] + data["b"])
```

请注意，使用 `@on_tools` 时，处理函数接收的是**参数字典**（`data`），而不是命名参数，并且必须返回一个字符串。

## 4. 刚刚发生了什么

- `@simple_tool` 从你的签名和文档字符串推断出 schema，然后将工具注册到全局 [ToolsManager](../api-reference/classes/ToolsManager.md) 中
- 智能体的[工具系统](../concepts/tool.md)将 schema 暴露给模型，在被调用时执行函数，并将结果作为 [ToolResult](../api-reference/classes/ToolResult.md) 返回

## 下一步

- [流式响应与回调](streaming.md)
- [使用事件拦截管道](event-hooks.md)
- 在[核心概念：工具系统](../concepts/tool.md)中了解工具执行细节
