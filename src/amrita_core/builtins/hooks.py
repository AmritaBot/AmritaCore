from amrita_core.config import AmritaConfig
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion
from amrita_core.protocol import MessageWithMetadata

posthook = on_completion(block=False, priority=10)


@posthook.handle()
async def cookie(event: CompletionEvent, config: AmritaConfig):
    response = event.get_model_response()
    if config.cookie.enable_cookie:
        if cookie := config.cookie.cookie:
            if cookie in response:
                await event.chat_object.yield_response(
                    response=MessageWithMetadata(
                        "Some error occurred, please try again later.",
                        metadata={
                            "type": "error",
                            "extra_type": "cookie",
                            "content": "Some error occurred, please try again later.",
                        },
                    )
                )
                await event.chat_object.set_queue_done()
