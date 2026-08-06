"""Peer push demo: reverse-stream messages land in the agent context.

Pushes a peer message *before* the agent starts; the first Step boundary
(``intro_step``) drains it and the model must see it.  Also pushes a
second message while the agent is running — it is picked up at the next
Step boundary (or dropped when the run finishes).

Usage: API_KEY=... python demo/peer_push_demo.py
"""

import asyncio
import os

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-v4-flash"


def build_config():
    from amrita_core.config import AmritaConfig, FunctionConfig

    return AmritaConfig(
        function_config=FunctionConfig(
            agent_tool_call_limit=8,
        )
    )


async def run() -> None:
    from amrita_core import create_agent, minimal_init
    from amrita_core.chatmanager import _step_workflow_rendered

    await minimal_init(build_config())
    agent = create_agent(
        base_url=BASE_URL,
        api_key=os.environ["API_KEY"],
        model=MODEL,
        model_config={"stream": True, "temperature": 0.3},
        config=build_config(),
    )
    chat = agent.get_chatobject(
        "Search the web for what AmritaCore is, then compute 17*3.",
        workflow=_step_workflow_rendered,
    )
    stream = chat.io_stream

    # Push BEFORE the run starts: drained at the first Step boundary.
    await stream.send_to_producer(
        "IMPORTANT: end your final answer with the exact line: [peer-acked]"
    )

    async def push_mid_run() -> None:
        # Push while the agent is working; lands at the next Step boundary
        # (or is dropped if the run finishes first).
        await asyncio.sleep(2.0)
        try:
            await stream.send_to_producer("mid-run peer note (may be dropped)")
        except Exception as e:
            print(f"[peer push failed: {type(e).__name__}: {e}]")

    push_task = asyncio.create_task(push_mid_run())
    print("--- stream ---")
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            if isinstance(msg, str):
                print(msg, end="", flush=True)
            else:
                content = getattr(msg, "content", None)
                if content:
                    print(f"\n[meta:{getattr(msg, 'metadata', None)}] {content}", flush=True)
    await push_task
    print("\n--- done ---")
    rs = chat._di_loop.run_state
    if rs is not None:
        print(f"steps={rs.step_index} phase={rs.current_phase} simple_mode={rs.simple_mode}")


if __name__ == "__main__":
    asyncio.run(run())
