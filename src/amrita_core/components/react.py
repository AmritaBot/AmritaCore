"""Agent ReAct loop nodes — strategy init, counter guard, execution, post-process.

```mermaid
graph TD
    BUILD_MESSAGE --> AGENT_ENTRY
    AGENT_ENTRY --> REACT_COUNTER
    REACT_COUNTER -->|increment & check| SINGLE_STRATEGY_CALL
    SINGLE_STRATEGY_CALL -->|success / fail & rollback| REACT_COUNTER
    REACT_COUNTER -->|BreakLoop| AGENT_POST_PROCESS
```
"""

from amrita_sense import POINTER_DEPENDS, Node, NodeType, WorkflowInterpreter
from amrita_sense.exceptions import BreakLoop
from amrita_sense.hook.matcher import Depends
from amrita_sense.logging import logger
from amrita_sense.streaming import SuspendObjectStream

from amrita_core.contents import MessageMetadataPayloadError, MessageWithMetadata
from amrita_core.contexts import (
    AbilityState,
    AgentLoopState,
    StrategyPayload,
    WorkingState,
)
from amrita_core.enums import SuspendEnum


@Node()
def AGENT_ENTRY(
    loop: AgentLoopState, mem: WorkingState, agent: StrategyPayload
) -> None:
    """Initialize the agent strategy and snapshot the current message context.

    Instantiates `loop.strategy` from the factory provided by `StrategyPayload`
    using `loop.stg_ctx`. Backs up `mem.context_wrap` into `loop.ctx_backup`
    so that the context can be rolled back on tool-call failure.

    Context Dependencies:
        * AgentLoopState  — receives `strategy` and `ctx_backup`.
        * WorkingState — provides `context_wrap` to snapshot.
        * StrategyPayload — provides the strategy factory.

    Upstream:
        * BUILD_MESSAGE — must have built `mem.context_wrap`.

    Downstream:
        * REACT_COUNTER — needs `loop.strategy`.
        * SINGLE_STRATEGY_CALL — needs `loop.strategy`, `loop.ctx_backup`.
        * AGENT_POST_PROCESS — needs `loop.strategy`.

    Suspend Point: none (no `SuspendEnum`).
    """
    assert loop.stg_ctx is not None
    loop.strategy = agent.strategy(loop.stg_ctx)
    if mem.context_wrap is None:
        raise ValueError(
            "Context wrap is not set, please set it before running the agent"
        )
    loop.ctx_backup = mem.context_wrap.copy()


@Node()
async def AGENT_POST_PROCESS(loop: AgentLoopState, wok: WorkingState):
    """Run strategy post-processing and extend context with end-messages.

    Calls `strategy.on_post_process()` (cleanup, logging, etc.) and appends
    `strategy.ctx.original_context.end_messages` to `wok.context_wrap` so
    the final strategy output is included in the conversation.

    Context Dependencies:
        * AgentLoopState — provides the strategy and its end_messages.
        * WorkingState — receives the extended `context_wrap`.

    Upstream:
        * AGENT_ENTRY — must have initialized `loop.strategy`.
        * SINGLE_STRATEGY_CALL (loop) — must have finished all tool calls.

    Downstream:
        * APPEND_RESPONSE / APPLY_CONTEXT — consume the extended context_wrap.

    Suspend Point: none (no `SuspendEnum`).
    """
    assert loop.strategy is not None, "Strategy is not initalized"
    await loop.strategy.on_post_process()
    assert wok.context_wrap is not None, "Context wrap is not set"
    wok.context_wrap.extend(loop.strategy.ctx.original_context.end_messages)


@Node(SuspendEnum.ADVANCE_COUNTER, False)
async def REACT_COUNTER(loop: AgentLoopState, ab: AbilityState):
    """Loop guard — increment the call counter; break when the limit is hit.

    ```mermaid
    flowchart TD
        C{loop.called_count > max_times?}
        C -->|yes| L[strategy.on_limited]
        L --> B[BreakLoop]
        C -->|no| I[called_count += 1]
        I --> S[Proceed to SINGLE_STRATEGY_CALL]
    ```

    The maximum is `ab.config.function_config.agent_tool_call_limit + 1`.
    When exceeded, `strategy.on_limited()` is called before raising `BreakLoop`.

    Context Dependencies:
        * AgentLoopState — reads/writes `called_count`; needs strategy.
        * AbilityState — provides `agent_tool_call_limit`.

    Upstream:
        * LOAD_STATE — must have loaded `ab.config`.
        * AGENT_ENTRY — must have initialized `loop.strategy`.

    Downstream:
        * SINGLE_STRATEGY_CALL — entered after the guard passes.

    Suspend Point:
        `SuspendEnum.ADVANCE_COUNTER` — intercepted after increment.
    """
    assert loop.strategy is not None
    max_times: int = ab.config.function_config.agent_tool_call_limit + 1
    if loop.called_count > max_times:
        await loop.strategy.on_limited()
        raise BreakLoop(f"Counter has reached the maximum limit of {max_times}")
    loop.called_count += 1


def SINGLE_STRATEGY_CALL(fallback_on_fail: bool = True) -> NodeType[bool]:
    """Factory: create a node that executes one agent strategy call.

    ```mermaid
    flowchart TD
        E[loop.strategy.single_execute]
        E -->|success| T[return True]
        E -->|exception| F{fallback_on_fail?}
        F -->|false| R[re-raise]
        F -->|true| P[Push error via object_io]
        P --> O[strategy.on_exception]
        O --> RB[Rollback context_wrap to ctx_backup]
        RB --> F2[return False]
    ```

    On failure with `fallback_on_fail=True`: streams an error message via
    `intp.object_io`, calls `strategy.on_exception()`, and restores
    `mem.context_wrap` from `loop.ctx_backup` before returning `False`.

    Context Dependencies:
        * AgentLoopState — provides `strategy` and `ctx_backup`.
        * WorkingState — provides `context_wrap` (rolled back on failure).
        * WorkflowInterpreter — streams error messages.

    Upstream:
        * AGENT_ENTRY — must have `loop.strategy` and `loop.ctx_backup`.
        * REACT_COUNTER — must pass the guard first.

    Downstream:
        * Returns `True` → loop back to `REACT_COUNTER`.
        * Returns `False` → upstream decides whether to terminate.

    Suspend Point:
        `SuspendEnum.SINGLE_TOOL` — intercepted during tool execution.

    Args:
        fallback_on_fail: If True, catch exceptions, rollback, return False.
                          If False, propagate the exception.

    Returns:
        A node function returning True on success, False on handled failure.
    """

    @Node(SuspendEnum.SINGLE_TOOL)
    async def _single_strategy_exec(
        loop: AgentLoopState,
        mem: WorkingState,
        intp: WorkflowInterpreter[SuspendObjectStream] = Depends(POINTER_DEPENDS),
    ) -> bool:
        assert loop.strategy is not None
        try:
            return await loop.strategy.single_execute()
        except Exception as e:
            if not fallback_on_fail and (isinstance(e, intp._exc_ignored)):
                raise
            logger.warning(
                f"ERROR\n{e!s}\n!Failed to call Strategy! Continuing with old data..."
            )
            await intp.object_io.yield_response(
                MessageWithMetadata(
                    content=f"Agent run failed:{e!s}",
                    metadata=MessageMetadataPayloadError(
                        error=str(e), type="error", extra_type=None
                    ),
                )
            )
            await loop.strategy.on_exception(e)
            assert loop.ctx_backup is not None
            mem.context_wrap = loop.ctx_backup
            return False

    return _single_strategy_exec
