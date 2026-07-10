import copy

from amrita_sense import Node
from amrita_sense.logging import logger

from amrita_core.contexts import (
    AbilityContext,
    AbilityState,
    DatabackendOptions,
    GeneralInput,
    MemoryContext,
    RespState,
    SessionMetadata,
    WorkingState,
)
from amrita_core.enums import SuspendEnum
from amrita_core.types.content import USER_INPUT
from amrita_core.types.message import Message, SendMessageWrap


@Node(SuspendEnum.MESSAGES_PREPARED, wrap_to_async=False)
def BUILD_MESSAGE(ip: GeneralInput, mem: MemoryContext, wok: WorkingState):
    train = ip.train
    data = mem.memory
    if data is None:
        raise RuntimeError(
            "Memory is not set, please run `LOAD_STATE` before building messages"
        )
    messages = [train, *copy.deepcopy(data.messages)]
    wok.context_wrap = SendMessageWrap.validate_messages(messages)


@Node(SuspendEnum.LOAD_STATE)
async def LOAD_STATE(
    opt: DatabackendOptions,
    ability: AbilityState,
    meta: SessionMetadata,
    mem: MemoryContext,
    rt_payload: WorkingState,
    ip: GeneralInput,
):
    logger.debug("Loading state..")
    slot = ability.slot
    if not (
        opt.skip_mcp_fetch
        or opt.skip_ability_extra_setting
        or opt.skip_tools_fetch
        or opt.skip_presets_fetch
    ):
        ability.ability = await slot.ability.load_ability_all(meta.session_id)
    else:
        if ability.ability is None:
            ability.ability = AbilityContext()
        if not opt.skip_mcp_fetch:
            ability.ability.mcp = await slot.ability.load_mcp_clients(meta.session_id)
        if not opt.skip_tools_fetch:
            ability.ability.tools = await slot.ability.load_tools(meta.session_id)
        if not opt.skip_presets_fetch:
            ability.ability.presets = await slot.ability.load_presets(meta.session_id)
    if not (opt.skip_memory_fetch):
        memory = await slot.memory.load_memory(meta.session_id)
        rt_payload.context_wrap = SendMessageWrap(
            ip.train,
            memory.messages,
            Message[USER_INPUT](role="user", content=ip.user_input),
        )
        mem.memory = memory
    if ability.preset is None and ability.ability is not None:
        ability.preset = ability.ability.presets.get_default_preset()


@Node(SuspendEnum.MEMORY)
def APPEND_RESPONSE(rt_payload: WorkingState, resp: RespState):
    if resp.response is None:
        raise ValueError("Response is None")
    if rt_payload.context_wrap is None:
        raise RuntimeError(
            "Context wrap is not set, please run `BUILD_MESSAGE` before appending response"
        )
    rt_payload.context_wrap.append(
        Message[str].model_validate(resp.response, from_attributes=True)
    )


@Node(SuspendEnum.APPLY_CONTEXT)
def APPLY_CONTEXT(mem: MemoryContext, rt_payload: WorkingState):
    if mem.memory is None:
        raise RuntimeError(
            "Memory is not set, please run `LOAD_STATE` before applying context"
        )
    if rt_payload.context_wrap is None:
        raise RuntimeError(
            "Context wrap is not set, please run `BUILD_MESSAGE` before applying context"
        )
    mem.memory.messages = rt_payload.context_wrap.unwrap(True)


@Node(SuspendEnum.COMMIT_MEMORY)
async def COMMIT_MEMORY(
    opt: DatabackendOptions,
    ability: AbilityState,
    meta: SessionMetadata,
    mem: MemoryContext,
) -> None:
    if mem.memory is None:
        raise RuntimeError("Memory is not set, please run `LOAD_STATE` before commit")
    if not opt.skip_memory_commit:
        await ability.slot.memory.commit_memory(meta.session_id, mem.memory)
