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
from amrita_sense.logging import debug_log, logger

from amrita_core.base.adapter import MessageContent
from amrita_core.components.compaction import ContextCompactor
from amrita_core.contexts import (
    AbilityState,
    GeneralInput,
    MemoryContext,
    RespState,
    WorkingState,
)
from amrita_core.enums import SuspendEnum
from amrita_core.exceptions import ContextOverflowError
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


async def _stream_completion(
    ability: AbilityState,
    wok: WorkingState,
    intp: WorkflowInterpreter,
    resp: RespState,
) -> UniResponse[str, None]:
    """Consume one completion stream, forwarding chunks to the client.

    The trailing ``UniResponse`` is returned; every other chunk is pushed onto
    the response stream. Provider usage is reported to the run ledger.
    """
    wrap = wok.context_wrap
    assert wrap is not None, (
        "Context wrap is not set, please run `BUILD_MESSAGE` before commit"
    )
    preset = ability.preset
    assert preset is not None, (
        "Preset is not set, please run `LOAD_STATE` before calling LLM"
    )
    response: UniResponse[str, None] | None = None
    async for chunk in call_completion(
        wrap.unwrap(),
        config=ability.config,
        preset=preset,
        usage=resp.usage,
    ):
        if isinstance(chunk, UniResponse):
            response = chunk
        elif isinstance(chunk, MessageContent | str):
            await intp.object_io.yield_response(chunk)
    if response is None:
        raise RuntimeError("No final response from chat adapter.")
    return response


async def _shrink_context(
    ability: AbilityState,
    wok: WorkingState,
    resp: RespState,
) -> bool:
    """Fold the oldest run context into a summary so a retry fits the window.

    Returns ``False`` when there is nothing to fold or the model produced no
    summary, which tells the caller to give up and surface the original error.
    """
    wrap = wok.context_wrap
    assert wrap is not None
    compactor = ContextCompactor(
        config=ability.config,
        preset=ability.preset,
        usage=resp.usage,
    )
    result = await compactor.fold(wrap.memory)
    if result is None:
        return False
    wrap.memory = [
        Message(
            role="user",
            content=f"[Summary of earlier conversation]\n{result.summary}",
        ),
        *result.messages,
    ]
    return True


@Node(SuspendEnum.LLM_CALL)
async def LLM_COMPLETION(
    ability: AbilityState,
    mem: MemoryContext,
    wok: WorkingState,
    intp: WorkflowInterpreter,
    resp: RespState,
):
    """Call the LLM completion API and stream chunks to the client.

    ```mermaid
    flowchart TD
        A[call_completion gateway] --> B[stream chunks]
        B -->|UniResponse| C[resp.response = UniResponse]
        B -->|text chunk| D[yield to client]
        B -->|context overflow| E[shrink context, retry once]
    ```

    Preset fallback is handled inside the ``call_completion`` gateway (it
    fires ``CompletionFallbackContext`` on failure), so this node only consumes
    the stream and forwards the final ``UniResponse``. A provider
    context-window rejection is not retried by the gateway; when
    ``config.llm.enable_overflow_recovery`` is on, this node folds the run
    context once and retries. The retry lives inside the node so that
    ``LLM_COMPLETION`` stays usable as a standalone workflow step, where a
    deferred retry would silently produce no response.

    Context Dependencies:
        * AbilityState — provides config and current preset.
        * MemoryContext — receives the measured prompt usage.
        * WorkingState — provides built `context_wrap`.
        * WorkflowInterpreter — streams chunks to the client.
        * RespState — receives the final `UniResponse` and the run ledger.

    Upstream:
        * LOAD_STATE — must have set `ability.preset`.
        * BUILD_MESSAGE — must have built `wok.context_wrap`.

    Downstream:
        * APPEND_RESPONSE — consumes `resp.response`.

    Suspend Point:
        `SuspendEnum.LLM_CALL` — intercepted during the LLM call.
    """
    logger.debug("Calling chat model..")
    recoveries = 1 if ability.config.llm.enable_overflow_recovery else 0
    for attempt in range(recoveries + 1):
        try:
            response = await _stream_completion(ability, wok, intp, resp)
        except ContextOverflowError as e:
            if attempt >= recoveries:
                raise
            logger.warning(
                "Provider rejected the request for exceeding its context "
                f"window ({e!s}); compacting and retrying once."
            )
            if not await _shrink_context(ability, wok, resp):
                raise
            continue
        resp.response = response
        if mem.memory is not None and response.usage is not None:
            # Remember the size this context reached so the next turn can decide whether to compact before calling the model again.
            mem.memory.usage = response.usage
        return
