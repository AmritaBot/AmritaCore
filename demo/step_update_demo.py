"""Real-API demo: autonomous plan revision via the update_step built-in.

Shows the native step-loop strategy (decompose -> execute -> leave) together
with the framework's plan-status injection and the model's ability to revise
its own plan when the plan objectively fails.

Scenario D1 (broken plan): step 2's tool returns a hard error.  The model
should retry at most once, then call update_step(remove_step) (or replan)
and finish with what step 1 gave.

Scenario D2 (control): all tools succeed, so no revision is expected.

Usage:
    export API_KEY=sk-...   # DeepSeek key
    python demo/step_update_demo.py [D1|D2]
"""

import asyncio
import os
import sys

from amrita_core import create_agent, on_tools, set_config
from amrita_core.builtins.agent.state import AgentRunState
from amrita_core.config import AmritaConfig, FunctionConfig
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"


def make_tools(fail_db: bool) -> None:
    """Register the two demo tools; db_query errors when fail_db is True."""

    search_def = FunctionDefinitionSchema(
        name="search_api",
        description="Search for data in the primary data store",
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

    @on_tools(search_def)
    async def search_api(data: dict[str, str]) -> str:
        return f"Search hit for '{data['query']}': AmritaCore 0.1.0 (found in primary store)."

    db_def = FunctionDefinitionSchema(
        name="db_query",
        description="Query the legacy database for complementary details",
        parameters=FunctionParametersSchema(
            type="object",
            properties={
                "table": FunctionPropertySchema(
                    type="string", description="Table name"
                ),
            },
            required=["table"],
        ),
    )

    @on_tools(db_def)
    async def db_query(data: dict[str, str]) -> str:
        if fail_db:
            return "ERROR: table 'legacy_cache' not found in database."
        return "DB row: version=0.1.0, release_date=2026-08-01."


async def run_scenario(name: str, user_input: str, fail_db: bool) -> None:
    print(f"\n{'=' * 60}")
    print(f"Scenario {name}: {user_input}")
    print("=" * 60)
    config = AmritaConfig(function_config=FunctionConfig(agent_tool_call_limit=20))
    set_config(config)
    agent = create_agent(
        base_url=BASE_URL,
        api_key=os.environ["API_KEY"],
        model=MODEL,
        model_config={"stream": True, "temperature": 0.3},
        config=config,
    )
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
        print(f"simple_mode={rs.simple_mode}")
        print(f"plan={[n.id for n in (rs.plan or [])]}")
        print(f"completed={rs.completed_step_ids}")
        print(f"plan_revision={rs.plan_revision}")
        print(f"stall_injected={rs.stall_injected}")
        print(f"last_summary={rs.last_summary}")
    else:
        print("(no run_state captured)")
    revised = bool(rs and rs.plan_revision > 0)
    print(f"plan_revision>0 => {'YES' if revised else 'NO'}")
    print(
        "Autonomous plan revision demonstrated."
        if revised
        else "No revision (expected for the control scenario)."
    )


async def main() -> None:
    which = sys.argv[1].upper() if len(sys.argv) > 1 else "D1"
    task = (
        "Use search_api to find the latest AmritaCore version, then use "
        "db_query to get complementary release details, then combine "
        "both into a final answer."
    )
    if which == "D2":
        make_tools(fail_db=False)
        await run_scenario("D2: control (all tools work)", task, fail_db=False)
    else:
        make_tools(fail_db=True)
        await run_scenario("D1: broken plan (db_query fails)", task, fail_db=True)


if __name__ == "__main__":
    asyncio.run(main())
