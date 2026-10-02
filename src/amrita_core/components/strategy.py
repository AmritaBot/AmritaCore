"""Strategy dispatch nodes — category predicates and the inline strategy runner.

Agent-category strategies run through the agent loop block (``AGENT_ENTRY`` and
friends). Every other category runs inline, exactly once, inside the main
workflow. Both paths consume the ``StrategyContext`` prepared by the ChatObject
runner beforehand.

```mermaid
flowchart LR
    P[prepare strategy context] --> C{get_category()}
    C -->|agent / agent-mixed| A[agent loop block]
    C -->|rag / workflow| I[RUN_INLINE_STRATEGY]
```
"""

import contextlib

from amrita_sense import Node, WorkflowInterpreter
from amrita_sense.hook.matcher import Depends
from amrita_sense.runtime.deps import POINTER_DEPENDS
from amrita_sense.streaming import SuspendObjectStream

from amrita_core.agent.strategy import (
    AgentStrategy,
    NoExceptionHandler,
    StrategyLikedObject,
)
from amrita_core.contexts import AgentLoopState, StrategyPayload, WorkingState
from amrita_core.enums import SuspendEnum

#: Categories whose strategies are driven by the agent loop block.
AGENT_CATEGORIES = ("agent", "agent-mixed")


def runs_in_agent_loop(strategy: type[AgentStrategy] | StrategyLikedObject) -> bool:
    """Whether a strategy is driven by the agent loop rather than run inline."""
    return strategy.get_category() in AGENT_CATEGORIES


@Node()
def is_agent_category(agent: StrategyPayload) -> bool:
    """Condition node: the active strategy runs through the agent loop."""
    return runs_in_agent_loop(agent.strategy)


@Node()
def not_agent_category(agent: StrategyPayload) -> bool:
    """Condition node: the active strategy runs inline in the main workflow."""
    return not runs_in_agent_loop(agent.strategy)


@Node(SuspendEnum.STRATEGY_START)
async def RUN_INLINE_STRATEGY(
    loop: AgentLoopState,
    agent: StrategyPayload,
    wok: WorkingState,
    intp: WorkflowInterpreter[SuspendObjectStream] = Depends(POINTER_DEPENDS),
) -> None:
    """Run a non-agent strategy once, then merge its end messages.

    The strategy's own output is appended to ``wok.context_wrap`` so the
    downstream completion and persistence nodes see it. Exceptions that the
    run declares ignorable are re-raised; every other failure is handed to
    ``on_exception`` unless the strategy opts out via ``NoExceptionHandler``.

    Context Dependencies:
        * AgentLoopState — provides the prepared `stg_ctx`.
        * StrategyPayload — provides the strategy factory.
        * WorkingState — receives the merged `context_wrap`.
        * WorkflowInterpreter — provides the exception-ignored set.

    Upstream: the strategy preparation node must have set `loop.stg_ctx`.

    Downstream: LLM_COMPLETION — consumes the merged `context_wrap`.

    Suspend Point: `SuspendEnum.STRATEGY_START`.
    """
    ctx = loop.stg_ctx
    if ctx is None:
        raise RuntimeError(
            "Strategy context is not prepared, please run the strategy "
            "preparation node before the inline runner"
        )
    st = agent.strategy(ctx)
    try:
        await st.run()
    except Exception as e:
        if isinstance(e, intp._exc_ignored):
            raise
        with contextlib.suppress(NoExceptionHandler):
            await st.on_exception(e)
    else:
        await st.on_post_process()
    if wok.context_wrap is None:
        raise RuntimeError(
            "Context wrap is not set, please run `BUILD_MESSAGE` before the "
            "inline runner"
        )
    wok.context_wrap.extend(ctx.original_context.end_messages)


__all__ = [
    "AGENT_CATEGORIES",
    "RUN_INLINE_STRATEGY",
    "is_agent_category",
    "not_agent_category",
    "runs_in_agent_loop",
]
