"""
Basic Example for AmritaCore - A simple demonstration of core functionality.

This example demonstrates the streaming response usage of AmritaCore.
"""

import asyncio

from amrita_core import ChatObject, init, load_amrita
from amrita_core.chatmanager import RESPONSE_TYPE
from amrita_core.config import AmritaConfig
from amrita_core.types import MemoryModel, Message


async def minimal_example():
    """
    A minimal example showing the essential steps to run AmritaCore with stream response.
    """
    print("\n🧪 Minimal Example")
    print("-" * 30)

    # Minimal configuration
    from amrita_core.config import set_config

    set_config(AmritaConfig())

    # Load AmritaCore
    await load_amrita()

    # Note: In a real scenario, you would configure your model preset here
    print("✅ AmritaCore loaded with minimal configuration")

    # Create context and system message
    context = MemoryModel()
    train = Message(content="You are a helpful assistant.", role="system")

    # Create and run a chat interaction
    chat = ChatObject(
        context=context,
        session_id="minimal_session",
        user_input="What can you do?",
        train=train.model_dump(),
    )
    # Collect response (just to show it works)
    i = 0
    async with chat.begin():
        async for chunk in chat.get_response_generator():
            print(
                chunk.get_content() if not isinstance(chunk, str) else chunk,
                end="",
                flush=True,
            )
            i += 1
    print(f"💬 Response length: {i} characters")
    print("✅ Minimal example completed!")


async def minimal_example_with_callback():
    """
    A minimal example showing the essential steps to run AmritaCore with stream response and with callback's using.
    """
    length: int = 0

    async def callback(message: RESPONSE_TYPE):
        nonlocal length
        print(message, end="")
        length += len(str(message))

    print("\n🧪With callback")
    print("-" * 30)
    from amrita_core.config import set_config

    set_config(AmritaConfig())
    await load_amrita()
    # Create context and system message
    context = MemoryModel()
    train = Message(content="You are a helpful assistant.", role="system")

    chat = ChatObject(
        context=context,
        session_id="minimal_session",
        user_input="What can you do?",
        train=train.model_dump(),
        callback=callback,  # Pass callback to ChatObject
    )
    # You can also use `chat.set_callback_func(callback)` to do it!
    # Collect response (just to show it works)
    await chat.begin()
    print(f"💬 Response length: {length} characters")
    print("✅ Example completed!")


if __name__ == "__main__":
    # Initialize AmritaCore
    init()
    asyncio.run(minimal_example())

    print("\n✨ All examples completed!")
