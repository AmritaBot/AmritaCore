from amrita_core.config import AmritaConfig
from amrita_core.contents import MessageWithMetadata
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

from .types import HookErrorMetadata

posthook = on_completion(block=False, priority=10)

_LEAK_RESPONSE = "Some error occurred, please try again later."
"""Substituted for any response that echoes the leak canary."""


@posthook.handle()
async def cookie(event: CompletionEvent, config: AmritaConfig):
    """Abort the response when the leak canary shows up in the model's output.

    The canary lives in the ``<HIDDEN>`` tag of the system prompt. Reasoning
    text is part of the model's output and is streamed to consumers as
    ``reasoning_chunk`` events, so checking only the answer would let a model
    that quotes the canary while thinking pass the guard.

    ``model_response`` and ``model_reasoning`` are rewritten as well, because
    the runner stores whatever the event carries on the response object and in
    the conversation history - a canary left there would come back through
    ``get_last_response()`` and the next turn's context. Chunks already handed
    to a streaming consumer cannot be retracted; the error payload appended
    here is what marks the run as failed.
    """
    response = event.get_model_response()
    if config.cookie.enable_cookie:
        if cookie := config.cookie.cookie:
            if cookie in response or cookie in (event.get_model_reasoning() or ""):
                event.model_response = _LEAK_RESPONSE
                event.model_reasoning = None
                await event.chat_object.io_stream.yield_response(
                    response=MessageWithMetadata(
                        _LEAK_RESPONSE,
                        metadata=HookErrorMetadata(
                            type="error",
                            extra_type="cookie",
                            content=_LEAK_RESPONSE,
                        ),
                    )
                )
                await event.chat_object.io_stream.set_queue_done()
