"""Real-API smoke test for HybridReActAgentStrategy (thinking mode)."""

import asyncio
import os

from amrita_core import create_agent, minimal_init, on_tools
from amrita_core.builtins.agent import HybridReActAgentStrategy
from amrita_core.chatmanager import ChatObject
from amrita_core.config import AmritaConfig, FunctionConfig
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-v4-flash"

SEARCH_DEFINITION = FunctionDefinitionSchema(
    name="web_search",
    description="Search the web for information",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "query": FunctionPropertySchema(
                type="string", description="Search query"
            ),
        },
        required=["query"],
    ),
)


@on_tools(SEARCH_DEFINITION)
async def web_search(data: dict[str, str]) -> str:
    q = data["query"]
    return f"Search result for '{q}': AmritaCore is an agent framework."


CALC_DEFINITION = FunctionDefinitionSchema(
    name="calculate",
    description="Perform a simple arithmetic calculation",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "expr": FunctionPropertySchema(
                type="string", description="Arithmetic expression"
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
    config = AmritaConfig(
        function_config=FunctionConfig(
            agent_tool_call_limit=8,
        )
    )
    await minimal_init(config)
    agent = create_agent(
        base_url=BASE_URL,
        api_key=os.environ["API_KEY"],
        model=MODEL,
        model_config={"stream": True, "temperature": 0.3},
        config=config,
    )
    agent.set_strategy(HybridReActAgentStrategy)

    chat: ChatObject = agent.get_chatobject(
        "Use web_search to find out what AmritaCore is, then use calculate to compute 17*3, then answer.",
    )
    print("--- stream ---")
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            if isinstance(msg, str):
                print(msg, end="", flush=True)
    print("\n--- done ---")


if __name__ == "__main__":
    asyncio.run(main())
