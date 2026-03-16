# Basic Example

## 2.3.1 Complete Basic Functionality Demonstration

Let's look at a more complete example that demonstrates context retention and multiple interactions using the simplified `create_agent` interface:

```python
"""
Basic Example for AmritaCore - A simple demonstration of core functionality.

This example shows how to create an agent, interact with it, and maintain
conversation context across multiple turns using the new unified API.
"""

import asyncio

from amrita_core import create_agent  # Main entry point
from amrita_core.logger import logger  # Optional logging


async def basic_example():
    """
    Basic example demonstrating core functionality with the new agent API.
    Shows agent creation, streaming responses, and automatic context retention.
    """
    print("🚀 Starting AmritaCore Basic Example (New API)")
    print("-" * 50)

    # Create an agent with minimal configuration
    # All necessary defaults (system prompt, context handling) are built-in
    agent = create_agent(
        base_url="https://api.example.com",           # Your API endpoint
        api_key="your-api-key",                        # Your API key
        model="gpt-3.5-turbo",                         # Model name
        model_config={                                  # Optional model parameters
            "temperature": 0.7,
            "stream": True,                             # Enable streaming
        }
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
        async for message in chat.get_response_generator():
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
        async for message in chat2.get_response_generator():
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

    # Create an agent with just the required parameters
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-4",
        model_config={"temperature": 0.7}
    )

    # Get a chat object and get the full response (non‑streaming)
    chat = agent.get_chatobject("你好，你能做什么？")

    async with chat.begin():
        response = await chat.full_response()

    print(f"💬 Response: {response}")
    print("✅ Minimal example completed!")


if __name__ == "__main__":
    # No explicit init() needed – create_agent handles everything
    asyncio.run(basic_example())
    asyncio.run(minimal_example())

    print("\n✨ All examples completed!")
```

## 2.3.2 Configuration Details

The new API simplifies configuration:

- **Agent creation**: `create_agent(base_url, api_key, model, model_config)` is the single entry point. It internally sets up default system prompts, context management, and model presets.
- **Model configuration**: Pass any model parameters (e.g., `temperature`, `stream`) as a dictionary via `model_config`. The `stream` flag controls whether responses are streamed.
- **Context handling**: The agent automatically retains conversation history. You do **not** need to manage `MemoryModel` or `train` messages manually – they are built in, unless you need to dump  or deserialize memory.
- **System prompt**: A sensible default system prompt is provided. If you need to customize it, `create_agent` accepts an optional `train` parameter.

## 2.3.3 Common Issue Troubleshooting

**Issue**: Connection errors to API endpoint  
**Solution**: Verify that `base_url` and `api_key` are correct and that your network can reach the endpoint.

**Issue**: High token usage in long conversations  
**Solution**: The agent automatically applies memory abstraction (if enabled in your backend) to summarize old messages. You can also adjust the `max_tokens` parameter in `model_config` to limit response length.

**Issue**: Slow responses  
**Solution**: Check network latency. For faster responses, consider using a smaller model or reducing `temperature` (which may make output more deterministic and slightly faster). Streaming (`stream=True`) also lets you start displaying text earlier.

**Issue**: Context seems lost between turns  
**Solution**: Ensure you are using the **same agent instance** for all turns in a conversation. Each `agent.get_chatobject()` call automatically uses the agent’s internal context.