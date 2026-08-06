# 基础示例

一个稍大的示例，展示你每天都会用到的三件事：**流式**、**工具**与**会话**。

> **你将看到**：第一轮 agent 调用你的 `calculate` 工具，第二轮（同一
> `session_id`）记得结果。如果你对工具或会话不熟，教程 2 和 5 有深入讲解。

```python
import asyncio
import os

from amrita_core import create_agent, minimal_init, on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

# 1. 在模块加载时注册一个工具。
CALC_DEFINITION = FunctionDefinitionSchema(
    name="calculate",
    description="Perform a simple arithmetic calculation",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "expr": FunctionPropertySchema(
                type="string", description="Arithmetic expression, e.g. '17*3'"
            ),
        },
        required=["expr"],
    ),
)


@on_tools(CALC_DEFINITION)
async def calculate(data: dict[str, str]) -> str:
    expr = data["expr"]
    try:
        return f"{expr} = {eval(expr)}"
    except Exception as e:  # noqa: S307
        return f"Error: {e!s}"


async def main() -> None:
    await minimal_init()
    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key=os.environ["OPENAI_API_KEY"],
        model="gpt-4o-mini",
    )

    # 2. 会话跨轮次保留记忆。
    chat = agent.get_chatobject(
        "What is 17*3? Use the calculate tool.",
        session_id="demo-session",
    )
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)

    # 3. 同一会话 → agent 记得上一轮。
    chat2 = agent.get_chatobject(
        "Double the number you just computed.",
        session_id="demo-session",
    )
    async with chat2.begin():
        async for msg in chat2.io_stream.get_response_generator():
            print(msg, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
```

## 引入的关键概念

- **`@on_tools(schema)`**：用 JSON Schema 注册工具——LLM 看到 schema，
  以校验过的参数调用你的函数。
- **`session_id`**：记忆的作用域键。两个 `ChatObject` 用同一 `session_id`
  则共享历史；不同 id 完全隔离。
- **流式**：`get_response_generator()` 产出每个 chunk；工作流还会发出结构化
  `MessageWithMetadata` 对象（Step 边界、工具调用）——见
  [流式与元数据](../tutorials/streaming.md)。

## 下一步

跟随[教程](../tutorials/index.md)——它们系统化递进：第一个 agent →
工具 → 流式 → 钩子 → 记忆。
