"""
Callback Function Example for AmritaCore

This example demonstrates how to use response callbacks to handle streaming
responses in real-time, which is useful for preventing queue overflow and
reducing latency in interactive applications.
"""

import asyncio
from typing import Any

from amrita_core import create_agent, minimal_init


async def response_callback(message: Any) -> None:
    """
    Response callback function that processes messages in real-time.

    This function is called for each message chunk as it arrives from the LLM.
    It's particularly useful for:
    - Preventing queue overflow in high-throughput scenarios
    - Reducing perceived latency in interactive applications
    - Real-time processing of streaming responses
    """
    # Process the message (could be a string or Message object)
    content = message if isinstance(message, str) else message.get_content()

    # Print with immediate flush to show real-time output
    print(content, end="", flush=True)


async def callback_example():
    """Demonstrate response callback functionality"""
    print("📞 Callback Function Example")
    print("-" * 30)

    # Create an agent
    await minimal_init()
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-3.5-turbo",
        model_config={"temperature": 0.7, "stream": True},
    )

    print("💬 Starting conversation with callback:")
    print()

    user_input = "Tell me a detailed story about a space adventure."

    print(f"👤 User: {user_input}")
    print("🤖 Assistant: ", end="")

    # Create chat object and set the callback
    chat = agent.get_chatobject(user_input)
    chat.set_callback_func(response_callback)

    # Execute with callback (no need to manually iterate)
    await chat.begin()

    print("\n")
    print("✅ Callback example completed!")


# Advanced callback example with error handling
async def advanced_callback_example():
    """Demonstrate advanced callback with error handling"""
    print("\n🚀 Advanced Callback Example")
    print("-" * 35)

    async def advanced_callback(message: Any) -> None:
        """Advanced callback with error handling and metadata processing"""
        try:
            if isinstance(message, str):
                # Handle string content
                print(message, end="", flush=True)
            else:
                # Handle Message object with metadata
                content = message.get_content()
                metadata = getattr(message, "metadata", None)

                if metadata:
                    msg_type = metadata.get("type", "unknown")
                    if msg_type == "middle_message":
                        print(f"[THINKING] {content}", end="", flush=True)
                    elif msg_type == "reasoning":
                        print(f"[REASONING] {content}", end="", flush=True)
                    elif msg_type == "function_call":
                        func_name = metadata.get("function_name", "unknown")
                        print(f"[CALLING] {func_name}...", end="", flush=True)
                    else:
                        print(content, end="", flush=True)
                else:
                    print(content, end="", flush=True)

        except Exception as e:
            print(f"[ERROR] {e!s}", end="", flush=True)

    # Create agent with middle message enabled
    await minimal_init()
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-4",
        model_config={"temperature": 0.7, "stream": True},
        function_config={
            "agent_middle_message": True,
            "tool_calling_mode": "agent",
        },
    )

    print("💬 Starting conversation with advanced callback:")
    print()

    user_input = "Think step by step about how to solve this math problem: 15 * 3 + 8"

    print(f"👤 User: {user_input}")
    print("🤖 Assistant: ", end="")

    chat = agent.get_chatobject(user_input)
    chat.set_callback_func(advanced_callback)

    await chat.begin()

    print("\n")
    print("✅ Advanced callback example completed!")


if __name__ == "__main__":
    # Run basic callback example
    asyncio.run(callback_example())

    # Run advanced callback example
    asyncio.run(advanced_callback_example())
