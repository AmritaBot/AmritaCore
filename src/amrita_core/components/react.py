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

from typing import TYPE_CHECKING

from amrita_sense import POINTER_DEPENDS, Node, NodeType, WorkflowInterpreter
from amrita_sense.exceptions import BreakLoop
from amrita_sense.hook.matcher import Depends
from amrita_sense.instructions.native import NATIVE_WHILE
from amrita_sense.logging import logger
from amrita_sense.streaming import SuspendObjectStream

if TYPE_CHECKING:
    from amrita_core.builtins.agent.react_base import BaseReActAgentStrategy
    from amrita_core.builtins.agent.state import Phase

from amrita_core.agent.context import build_strategy_context
from amrita_core.builtins.agent.state import AgentRunState
from amrita_core.contents import MessageMetadataPayloadError, MessageWithMetadata
from amrita_core.contexts import (
    AbilityState,
    AgentLoopState,
    GeneralInput,
    RespState,
    SessionMetadata,
    StrategyPayload,
    WorkingState,
)
from amrita_core.enums import SuspendEnum
from amrita_core.types.message import Message, SendMessageWrap


@Node(tag="subconscious_strategy_init")
async def STRATEGY_INIT(
    input_ctx: GeneralInput,
    loop: AgentLoopState,
    wok: WorkingState,
    ab: AbilityState,
    resp: RespState,
    session: SessionMetadata,
    intp: WorkflowInterpreter[SuspendObjectStream] = Depends(POINTER_DEPENDS),
) -> None:
    """Initialize the strategy context.

    Equivalent to the `_run_strategy('agent' branch)` in chat_object.py.
    AGENT_ENTRY is executed right after, and agent.strategy(loop.stg_ctx)
    instantiates ReActAgentStrategy.

    Populates ``StrategyContext`` with DI resource fields so that strategies
    can access preset, config, io_stream, tools_manager, etc. via the
    ``_StrategyBase`` convenience properties without reaching through
    ``chat_object``.
    """
    assert wok.context_wrap is not None, "Context wrap must be built before strategy"

    context = SendMessageWrap.validate_messages(
        [input_ctx.train, Message(role="user", content=input_ctx.user_input)]
    )
    loop.stg_ctx = build_strategy_context(
        user_input=input_ctx.user_input,
        original_context=context,
        preset=ab.preset,
        config=ab.config,
        tools_manager=ab.ability.tools if ab.ability else None,
        io_stream=intp.object_io,
        train_content=input_ctx.train.content,
        stream_id=session.stream_id,
        usage=resp.usage,
    )


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
    if loop.run_state is None:
        loop.run_state = AgentRunState()
    # Bridge the SAME run_state instance between loop and strategy so that
    # conditions/hooks observe identical state (step strategies only).
    strategy = loop.strategy
    if isinstance(strategy, _step_strategy_guard()):
        if strategy.run_state is None:
            strategy.run_state = loop.run_state
        else:
            loop.run_state = strategy.run_state


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
        raise BreakLoop(
            f"Counter has reached the maximum limit of {max_times}, reset loop.called_count to 0 to continue"
        )
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
        * Returns `True` -> loop back to `REACT_COUNTER`.
        * Returns `False` -> upstream decides whether to terminate.

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


# Native step-loop nodes (additive over legacy SINGLE_STRATEGY_CALL /
# REACT_COUNTER; wired via NATIVE_DO/NATIVE_WHILE in workflows.py).


def _step_strategy_guard() -> type["BaseReActAgentStrategy"]:
    """Resolve the strategy class required by the native step loop.

    Imported lazily to avoid a circular import (``builtins.agent`` imports
    workflow components).  Used as the isinstance guard so that the step
    lifecycle hooks (``intro_step`` / ``leave_step`` / ``run_state``) are
    only called on strategies that actually provide them.
    """
    from amrita_core.builtins.agent.react_base import BaseReActAgentStrategy

    return BaseReActAgentStrategy


def _step_strategy(loop: AgentLoopState) -> "BaseReActAgentStrategy":
    """Resolve the strategy for the native step loop (isinstance guard).

    The step-loop nodes (``STEP_INTRO`` / ``STEP_EXEC`` / ``STEP_LEAVE`` /
    ``STEP_SLOT``) require the step lifecycle hooks ``intro_step`` /
    ``leave_step`` / ``run_state``, provided by ``BaseReActAgentStrategy``
    and its subclasses.
    """
    strategy = loop.strategy
    if not isinstance(strategy, _step_strategy_guard()):
        raise RuntimeError(
            "Native step-loop requires a BaseReActAgentStrategy subclass, "
            f"got {type(strategy).__name__}"
        )
    return strategy


@Node(SuspendEnum.STEP_INTRO)
async def STEP_INTRO(loop: AgentLoopState):
    """Step entry boundary — calls ``strategy.intro_step()``.

    The ``@Node(SuspendEnum.STEP_INTRO)`` tag doubles as the interpreter-level
    suspend point (``_call()`` waits on ``node.tag`` before executing), so no
    manual ``_wait_for_continue`` is needed.
    """
    assert loop.run_state is not None
    await _step_strategy(loop).intro_step()


@Node(SuspendEnum.SINGLE_TOOL)
async def STEP_EXEC(
    loop: AgentLoopState,
    mem: WorkingState,
    intp: WorkflowInterpreter[SuspendObjectStream] = Depends(POINTER_DEPENDS),
) -> bool:
    """Execute one strategy iteration (single tool round) with rollback.

    Error handling mirrors the legacy ``SINGLE_STRATEGY_CALL(fallback_on_fail=True)``
    path: on failure, stream an error, call ``strategy.on_exception()`` and
    restore ``mem.context_wrap`` from ``loop.ctx_backup``.

    Also advances ``loop.called_count`` (replacing the legacy REACT_COUNTER)
    and records ``run_state.exec_finished`` when the strategy reports it is
    done calling tools.
    """
    assert loop.strategy is not None
    loop.called_count += 1
    try:
        result = await loop.strategy.single_execute()
    except Exception as e:
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
        result = False
    if loop.run_state is not None and result:
        # Per-iteration hook runs inside the loop so a stalled agent stops
        # burning tokens (leave_step only runs after the loop exits).
        strategy = _step_strategy(loop)
        await strategy.after_iteration()
    elif loop.run_state is not None and not result:
        # No more tool calls: the execute-phase iteration loop can end.
        loop.run_state.exec_finished = True
    return result


@Node(SuspendEnum.STEP_LEAVE)
async def STEP_LEAVE(loop: AgentLoopState):
    """Step exit boundary — calls ``strategy.leave_step()``."""
    assert loop.run_state is not None
    await _step_strategy(loop).leave_step()


def STEP_SLOT(phase: "Phase"):
    """Factory: build an intro/leave node pair for a reasoning phase.

    Args:
        phase: one of ``"analyze"``, ``"plan"``, ``"execute"``, ``"verify"``.

    Returns:
        ``(intro_node, leave_node)`` — both are ``@Node`` with a phase-specific
        tag that doubles as the interpreter-level suspend point.
    """

    @Node(f"ChatObject::step_{phase}_intro")
    async def _intro(loop: AgentLoopState):
        assert loop.strategy is not None
        await _step_strategy(loop).intro_step(phase=phase)

    @Node(f"ChatObject::step_{phase}_leave")
    async def _leave(loop: AgentLoopState):
        assert loop.strategy is not None
        await _step_strategy(loop).leave_step(phase=phase)

    return _intro, _leave


@Node()
async def task_cond(loop: AgentLoopState, ab: AbilityState) -> bool:
    """Task-loop condition (single ``Node[bool]``).

    Stops when the tool-call limit is reached, the strategy suggests stop,
    the strategy finished calling tools (``exec_finished``), or a stall was
    detected and the give-up prompt injected.
    """
    assert loop.strategy is not None
    max_times: int = ab.config.function_config.agent_tool_call_limit + 1
    if loop.called_count > max_times:
        await loop.strategy.on_limited()
        return False
    if getattr(loop.strategy, "_suggested_stop", False):
        return False
    if loop.run_state is None:
        return True
    if loop.run_state.stall_injected:
        return False
    if loop.run_state.simple_mode:
        # Bare run: one implicit execute Step; stop when the strategy is done.
        return not loop.run_state.exec_finished
    # Plan mode: keep walking the topological order until every node is done.
    return not loop.run_state.all_plan_done()


@Node()
async def iter_cond(loop: AgentLoopState, ab: AbilityState) -> bool:
    """Within-Step iteration condition (single ``Node[bool]``).

    Continues while this Step (one DAG node, or the implicit execute Step in
    simple mode) still has tool calls to make: no stall injected, no budget
    exhausted, the strategy has not finished calling tools and has not
    suggested stopping.

    Hard stop: the tool-call limit (``agent_tool_call_limit``) is enforced
    here as well — the inner iteration loop must never burn tokens past the
    configured limit, regardless of what the strategy decides.
    """
    assert loop.strategy is not None
    rs = loop.run_state
    if rs is None:
        return False
    max_times: int = ab.config.function_config.agent_tool_call_limit + 1
    if loop.called_count > max_times:
        await loop.strategy.on_limited()
        return False
    if rs.stall_injected:
        return False
    if rs.step_started_ts is not None:
        rs.tokens.refresh_window(loop.strategy.usage, rs.step_started_ts)
    if rs.tokens.exhausted:
        return False
    if rs.exec_finished:
        return False
    return not getattr(loop.strategy, "_suggested_stop", False)


@Node()
async def simple_mode(loop: AgentLoopState) -> bool:
    """Whether the LLM decided to run the task directly (no decomposition)."""
    return bool(loop.run_state and loop.run_state.simple_mode)


# STEP_BODY — node-driven step-loop body (shared with workflows.py and
# chat_object.py): each task-loop iteration is ONE Step = ONE DAG node.
NODE_INTRO, NODE_LEAVE = STEP_SLOT("node")

# BREAK_LOOP cannot sit inside a NATIVE_IF branch (DFS scanner configures
# loop-control nodes pre-expansion); plan completion lives in task_cond.
STEP_BODY = NODE_INTRO >> NATIVE_WHILE(iter_cond).ACTION(STEP_EXEC) >> NODE_LEAVE
