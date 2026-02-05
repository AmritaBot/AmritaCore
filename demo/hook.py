"""
Basic Hook Example for AmritaCore - Demonstrates registering and using hooks.

This example shows how to register event handlers for different types of events
and how to print messages when events occur.
"""

from amrita_core.hook.event import CompletionEvent, PreCompletionEvent
from amrita_core.hook.on import on_completion, on_precompletion
from amrita_core.logging import logger


# Register a hook for completion events (after AI responds)
@on_completion(priority=10, block=False).handle()  # block=False to allow other handlers
async def on_ai_respond(event: CompletionEvent):
    """
    This handler runs when the AI completes a response.
    """
    logger.info(f"✅ Hook triggered: AI responded with: {event.model_response[:50]}...")
    logger.info(f"📝 Full response: {event.model_response}")


# Register a hook for pre-completion events (before AI responds)
@on_precompletion(priority=5, block=False).handle()  # Lower priority executes first
async def on_before_ai_respond(event: PreCompletionEvent):
    """
    This handler runs before the AI responds.
    """
    user_input = event.user_input
    logger.info(f"🔍 Hook triggered: About to respond to user input: {user_input}")
    logger.info(
        f"📋 Context messages count: {len(event.get_context_messages().unwrap())}"
    )
