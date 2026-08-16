"""
Basic Example for AmritaCore - A simple demonstration of core functionality.

This example shows how to create an agent, interact with it, and maintain
conversation context across multiple turns using the new unified API.
"""

import asyncio

from amrita_sense.logging import logger  # Optional logging

from amrita_core import create_agent, minimal_init  # Main entry point


async def basic_example():
    """
    Basic example demonstrating core functionality with the new agent API.
    Shows agent creation, streaming responses, and automatic context retention.
    """
    print("🚀 Starting AmritaCore Basic Example (New API)")
    print("-" * 50)

    # Create an agent with minimal configuration
    # All necessary defaults (system prompt, context handling) are built-in
    await minimal_init()
    agent = create_agent(
        base_url="https://api.example.com",  # Your API endpoint
        api_key="your-api-key",  # Your API key
        model="gpt-3.5-turbo",  # Model name
        model_config={  # Optional model parameters
            "temperature": 0.7,
            "stream": True,  # Enable streaming
        },
    )
    logger.info("✅ Agent created successfully.")

    print("💬 Starting a sample conversation:")
    print()

    # Example 1: First interaction
    user_input = "Hello! Can you tell me what AmritaCore is?"

    print(f"👤 User: {user_input}")

    # Get a chat object for this user input
    chat = agent.get_chatobject(user_input)

    print("🤖 Assistant: ", end="")

    # Stream the response token by token
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            # message can be a string or a Message object
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")

    print("\n")  # New line after response

    # Example 2: Follow-up question – context is automatically retained by the agent
    follow_up = "Can you explain its main features?"

    print(f"👤 User: {follow_up}")

    # Simply create another chat object with the same agent
    chat2 = agent.get_chatobject(follow_up)

    print("🤖 Assistant: ", end="")

    async with chat2.begin():
        async for message in chat2.io_stream.get_response_generator():
            content = message if isinstance(message, str) else message.get_content()
            print(content, end="")

    print("\n")  # New line after response

    print("🎉 Basic example completed successfully!")
    print("-" * 50)
    print("💡 Key concepts demonstrated:")
    print("   • Agent creation with create_agent()")
    print("   • Obtaining chat objects via agent.get_chatobject()")
    print("   • Streaming responses")
    print("   • Automatic context retention across turns")
    print("   • Built‑in default system prompt")


async def minimal_example():
    """
    A minimal example showing the essential steps to run AmritaCore.
    """
    print("\n🧪 Minimal Example")
    print("-" * 30)
    await minimal_init()
    # Create an agent with just the required parameters
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-4",
        model_config={"temperature": 0.7},
    )

    # Get a chat object and get the full response (non‑streaming)
    chat = agent.get_chatobject("Hello, what can you do?")

    async with chat.begin():
        response = await chat.full_response()

    print(f"💬 Response: {response}")
    print("✅ Minimal example completed!")


if __name__ == "__main__":
    # No explicit init() needed – create_agent handles everything
    asyncio.run(basic_example())
    asyncio.run(minimal_example())

    print("\n✨ All examples completed!")
