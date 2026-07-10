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
    assert loop.stg_ctx is not None
    loop.strategy = agent.strategy(loop.stg_ctx)
    if mem.context_wrap is None:
        raise ValueError(
            "Context wrap is not set, please set it before running the agent"
        )
    loop.ctx_backup = mem.context_wrap.copy()


@Node()
async def AGENT_POST_PROCESS(loop: AgentLoopState, wok: WorkingState):
    assert loop.strategy is not None, "Strategy is not initalized"
    await loop.strategy.on_post_process()
    assert wok.context_wrap is not None, "Context wrap is not set"
    wok.context_wrap.extend(loop.strategy.ctx.original_context.end_messages)


@Node(SuspendEnum.ADVANCE_COUNTER, False)
async def REACT_COUNTER(loop: AgentLoopState, ab: AbilityState):
    assert loop.strategy is not None
    max_times: int = ab.config.function_config.agent_tool_call_limit + 1
    if loop.called_count > max_times:
        await loop.strategy.on_limited()
        raise BreakLoop(f"Counter has reached the maximum limit of {max_times}")
    loop.called_count += 1


def SINGLE_STRATEGY_CALL(fallback_on_fail: bool = True) -> NodeType[bool]:
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
