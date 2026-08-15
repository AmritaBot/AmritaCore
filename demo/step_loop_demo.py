"""Real-API smoke test for the native step-loop built-in ReAct strategy.

Talks to any OpenAI-compatible endpoint using ``$API_KEY`` from the
environment.  The adapter (protocol) is chosen by the framework's default
(OpenAI-compatible); the provider is decided by ``API_BASE_URL`` and
``API_MODEL`` — DeepSeek is just one example.  Three scenarios:

- A: simple QA  -> verify simple-mode bare run (no decomposition)
- B: multi-tool -> verify decomposition -> execute iterations -> subject-predicate
- C: stall      -> verify "give up" prompt injection and immediate Step end

Usage:
    export API_KEY=sk-...        # provider API key
    export API_BASE_URL=...      # optional, defaults below
    export API_MODEL=...         # optional, defaults below
    python demo/step_loop_demo.py [A|B|C]
"""

import asyncio
import os
import sys

from amrita_core import minimal_init, on_tools
from amrita_core.builtins.agent.state import AgentRunState
from amrita_core.config import AmritaConfig, FunctionConfig
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

BASE_URL = os.environ.get("API_BASE_URL", "https://api.deepseek.com")
MODEL = os.environ.get("API_MODEL", "deepseek-chat")

SEARCH_DEFINITION = FunctionDefinitionSchema(
    name="web_search",
    description="Search the web for information",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "query": FunctionPropertySchema(
                type="string", description="The search query"
            ),
        },
        required=["query"],
    ),
)


@on_tools(SEARCH_DEFINITION)
async def web_search(data: dict[str, str]) -> str:
    q = data["query"]
    # Deterministic canned result so stall detection is reproducible.
    return f"Search result for '{q}': AmritaCore is an agent framework (canned)."


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
    except Exception as e:
        return f"Error: {e!s}"


def build_config(stall: bool = False) -> AmritaConfig:
    config = AmritaConfig(
        function_config=FunctionConfig(
            agent_tool_call_limit=15,
        )
    )
    if stall:
        config.builtin.loop_reasoning_trigger = 3
    return config


async def run_scenario(name: str, user_input: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"Scenario {name}: {user_input}")
    print("=" * 60)
    from amrita_core import create_agent

    agent = create_agent(
        base_url=BASE_URL,
        api_key=os.environ["API_KEY"],
        model=MODEL,
        model_config={"stream": True, "temperature": 0.3},
        config=build_config(stall=(name == "C")),
    )
    # Use the native step-loop workflow (ChatObject-compatible variant).
    from amrita_core.chatmanager import _step_workflow_rendered

    chat = agent.get_chatobject(user_input, workflow=_step_workflow_rendered)
    print("\n--- stream ---")
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            if isinstance(msg, str):
                print(msg, end="", flush=True)
            else:
                content = getattr(msg, "content", None)
                if content:
                    print(
                        f"\n[meta:{getattr(msg, 'metadata', None)}] {content}",
                        flush=True,
                    )
    print("\n--- run state ---")
    rs: AgentRunState | None = chat._di_loop.run_state
    if rs is not None:
        print(f"step_index={rs.step_index}")
        print(f"current_phase={rs.current_phase}")
        print(f"simple_mode={rs.simple_mode}")
        print(f"plan={[n.id for n in (rs.plan or [])]}")
        print(f"completed={rs.completed_step_ids}")
        print(f"stall_injected={rs.stall_injected}")
        print(f"tool_signatures={rs.step_tool_signatures}")
        print(f"last_summary={rs.last_summary}")
        print(f"tokens={rs.tokens.model_dump()}")
    else:
        print("(no run_state captured)")


async def main() -> None:
    await minimal_init(build_config())
    which = sys.argv[1].upper() if len(sys.argv) > 1 else "A"

    scenarios = {
        "A": ("A: simple QA", "What is 2+2? Answer directly."),
        "B": (
            "B: multi-tool",
            "Search the web for 'AmritaCore', then calculate 17*3, "
            "and tell me what you found.",
        ),
        "C": (
            "C: stall",
            "Keep searching the web for 'AmritaCore' repeatedly until I stop you.",
        ),
    }
    name, prompt = scenarios[which]
    await run_scenario(name, prompt)


if __name__ == "__main__":
    asyncio.run(main())
