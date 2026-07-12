"""Core processing workflow — state loading, message building, and persistence.

```mermaid
graph TD
    LOAD_STATE["LOAD_STATE<br/>(entry point)"]
    LOAD_STATE --> JINJA2_RENDER --> BUILD_MESSAGE --> LLM_COMPLETION
    LOAD_STATE -.->|provides memory, preset| CHAIN[...]
    LLM_COMPLETION --> APPEND_RESPONSE --> APPLY_CONTEXT --> COMMIT_MEMORY
```
"""

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
    """Merge the rendered train message with memory into a SendMessageWrap.

    Deep-copies `memory.messages`, prepends `ip.train`, validates the
    combined list, and stores it as `wok.context_wrap` for downstream
    LLM and agent nodes.

    Context Dependencies:
        * GeneralInput  — provides rendered train message.
        * MemoryContext — provides historical messages.
        * WorkingState  — receives the built `context_wrap`.

    Upstream:
        * LOAD_STATE — must have set `mem.memory`.
        * JINJA2_RENDER — must have rendered `ip.train`.

    Downstream:
        * LLM_COMPLETION — consumes `wok.context_wrap`.
        * AGENT_ENTRY — consumes `wok.context_wrap`.

    Suspend Point:
        `SuspendEnum.MESSAGES_PREPARED` — intercepted after messages are ready.
    """
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
    """Entry point — load session state from the backend.

    ```mermaid
    flowchart TD
        subgraph Backend
            S[BackendSlots]
        end
        S -->|load_ability_all| AA[ability.ability]
        S -->|load_memory| MM[mem.memory]
        MM --> CW[Build initial context_wrap<br/>train + history + user_input]
        AA -->|get_default_preset| PR[ability.preset]
    ```

    Loads tools, presets, MCP clients, and memory. Supports fine-grained
    skip options via `DatabackendOptions` for incremental reloads.

    Context Dependencies:
        * DatabackendOptions — controls which resources to skip.
        * AbilityState — provides backend slots; receives ability & preset.
        * SessionMetadata — provides `session_id` for backend queries.
        * MemoryContext — receives loaded memory.
        * WorkingState — receives initial `context_wrap`.
        * GeneralInput — provides train + user_input for context_wrap.

    Upstream: none — this is the workflow entry point.

    Downstream:
        * JINJA2_RENDER — needs `mem.memory`, `ability.config`.
        * BUILD_MESSAGE — needs `mem.memory`.
        * LLM_COMPLETION — needs `ability.preset`.
        * APPLY_CONTEXT / COMMIT_MEMORY — need `mem.memory`.
        * REACT_COUNTER — needs `ability.config`.

    Suspend Point:
        `SuspendEnum.LOAD_STATE` — intercepted during state loading.
    """
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
    """Append the final LLM response as a Message to the context wrap.

    Converts `resp.response` (a `UniResponse`) into a `Message` and appends
    it to `rt_payload.context_wrap`, making the assistant reply part of the
    conversation context.

    Context Dependencies:
        * WorkingState — reads/writes `context_wrap`.
        * RespState — provides the final `UniResponse`.

    Upstream:
        * BUILD_MESSAGE — must have built `context_wrap`.
        * LLM_COMPLETION — must have produced `resp.response`.

    Downstream:
        * APPLY_CONTEXT — consumes the updated `context_wrap`.

    Suspend Point:
        `SuspendEnum.MEMORY` — intercepted after appending, before writing back.
    """
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
    """Unwrap the context wrap and write messages back into memory.

    Unwraps all messages from `rt_payload.context_wrap` and assigns them to
    `mem.memory.messages`, persisting this turn's changes into the
    `MemoryContext`.

    Context Dependencies:
        * MemoryContext — receives the final message list.
        * WorkingState — provides the built `context_wrap`.

    Upstream:
        * LOAD_STATE — must have set `mem.memory`.
        * BUILD_MESSAGE — must have built `context_wrap`.
        * APPEND_RESPONSE — must have appended the response.

    Downstream:
        * COMMIT_MEMORY — consumes the updated `mem.memory` for persistence.

    Suspend Point:
        `SuspendEnum.APPLY_CONTEXT` — intercepted during context application.
    """
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
    """Persist memory to the backend storage (terminal node).

    Commits `mem.memory` via `ability.slot.memory.commit_memory()` so that
    conversation history survives beyond the current request. Honours
    `DatabackendOptions.skip_memory_commit` to skip persistence.

    Context Dependencies:
        * DatabackendOptions — controls whether to skip the commit.
        * AbilityState — provides backend slot (`slot.memory`).
        * SessionMetadata — provides `session_id` as storage key.
        * MemoryContext — provides memory data to persist.

    Upstream:
        * LOAD_STATE — must have set `mem.memory` and `ability.slot`.
        * APPLY_CONTEXT — must have written latest messages to `mem.memory`.

    Downstream: none — terminal node of the workflow.

    Suspend Point:
        `SuspendEnum.COMMIT_MEMORY` — intercepted during memory commit.
    """
    if mem.memory is None:
        raise RuntimeError("Memory is not set, please run `LOAD_STATE` before commit")
    if not opt.skip_memory_commit:
        await ability.slot.memory.commit_memory(meta.session_id, mem.memory)
