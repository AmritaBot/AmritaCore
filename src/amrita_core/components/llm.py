"""LLM-related workflow nodes — template rendering and completion calling.

```mermaid
graph LR
    LOAD_STATE --> JINJA2_RENDER
    LOAD_STATE --> BUILD_MESSAGE --> LLM_COMPLETION
    JINJA2_RENDER --> BUILD_MESSAGE
```
"""

import asyncio

from amrita_sense import Node, WorkflowInterpreter
from amrita_sense.hook.matcher import MatcherFactory
from amrita_sense.logging import debug_log, logger

from amrita_core.base.adapter import MessageContent
from amrita_core.contexts import (
    AbilityState,
    GeneralInput,
    MemoryContext,
    RespState,
    WorkingState,
)
from amrita_core.enums import SuspendEnum
from amrita_core.hook.event import FallbackContext
from amrita_core.hook.exception import FallbackFailed
from amrita_core.libchat import call_completion
from amrita_core.types.message import Message
from amrita_core.types.response import UniResponse


@Node(SuspendEnum.TRAIN_RENDER)
async def JINJA2_RENDER(
    ability: AbilityState,
    mem: MemoryContext,
    ip: GeneralInput,
):
    """Render the train template via Jinja2 and append the user message to memory.

    Appends `ip.user_input` to `memory.messages`, then uses the Jinja2 template
    to render `ip.train` with `memory`, `config`, and custom `jinja2_vars`
    injected as template context variables.

    Context Dependencies:
        * AbilityState — provides runtime config.
        * MemoryContext — provides session memory.
        * GeneralInput  — provides user input, template, and render vars.

    Upstream:
        * LOAD_STATE — must have set `mem.memory`.

    Downstream:
        * BUILD_MESSAGE — consumes the rendered `ip.train`.

    Suspend Point:
        `SuspendEnum.TRAIN_RENDER` — intercepted during template rendering.
    """
    logger.debug("Starting JINJA2 template rendering..")
    data = mem.memory
    if data is None:
        raise RuntimeError(
            "Memory is not set, please run `LOAD_STATE` before rendering"
        )
    config = ability.config

    data.messages.append(Message(role="user", content=ip.user_input))

    logger.debug(
        f"Added user message to memory, current message count: {len(data.messages)}"
    )
    # train,memory,chatobj(ChatObject),config will be given to Jinja2
    ip.train = Message.model_validate(ip.train, from_attributes=True)
    ip.train.content = await asyncio.to_thread(
        ip.template.render,
        train=ip.train,
        memory=data,
        config=config,
        **ip.jinja2_vars,
    )
    debug_log(ip.train.content)


@Node(SuspendEnum.LLM_CALL)
async def LLM_COMPLETION(
    ability: AbilityState,
    wok: WorkingState,
    intp: WorkflowInterpreter,
    resp: RespState,
):
    """Call the LLM completion API with preset fallback and retry logic.

    ```mermaid
    flowchart TD
        A[Current Preset] --> B[call_completion stream]
        B -->|success| C[resp.response = UniResponse]
        B -->|exception| D[Fire FallbackContext hook]
        D --> E{New preset available?}
        E -->|yes| F[Switch preset & retry]
        F --> A
        E -->|no| G[FallbackFailed]
    ```

    Streams chunks via `WorkflowInterpreter.object_io`. On failure, fires the
    `FallbackContext` event hook to try alternate presets, up to
    `max_fallbacks` times.

    Context Dependencies:
        * AbilityState — provides config and current preset.
        * WorkingState — provides built `context_wrap`.
        * WorkflowInterpreter — streams chunks to the client.
        * RespState — receives the final `UniResponse`.

    Upstream:
        * LOAD_STATE — must have set `ability.preset`.
        * BUILD_MESSAGE — must have built `wok.context_wrap`.

    Downstream:
        * APPEND_RESPONSE — consumes `resp.response`.

    Suspend Point:
        `SuspendEnum.LLM_CALL` — intercepted during the LLM call.
    """
    logger.debug("Calling chat model..")
    response: UniResponse[str, None] | None = None
    used_preset: set[str] = set()
    assert wok.context_wrap is not None, (
        "Context wrap is not set, please run `BUILD_MESSAGE` before commit"
    )
    assert ability.preset is not None, (
        "Preset is not set, please run `LOAD_STATE` before calling LLM"
    )
    for i in range(1, ability.config.llm.max_fallbacks + 1):
        try:
            used_preset.add(ability.preset.name)
            async for chunk in call_completion(
                wok.context_wrap.unwrap(),
                config=ability.config,
                preset=ability.preset,
            ):
                if isinstance(chunk, UniResponse):
                    response = chunk
                elif isinstance(chunk, MessageContent | str):
                    await intp.object_io.yield_response(chunk)
            break
        except Exception as e:
            logger.warning(
                f"Because of `{e!s}`, LLM request failed, retrying ({i}/{ability.config.llm.max_retries})..."
            )
            ctx = FallbackContext(
                ability.preset, e, ability.config, wok.context_wrap, i
            )
            await MatcherFactory.trigger_event(
                ctx, ctx.config, exception_ignored=(FallbackFailed,)
            )
            if ctx.preset is ability.preset:
                ctx.fail("No preset fallback available, exiting!")
            ability.preset = ctx.preset
    else:
        raise FallbackFailed("Max preset fallbacks retries exceeded.")
    if response is None:
        raise RuntimeError("No final response from chat adapter.")
    resp.response = response
