# Basic Example

## 2.3.1 Complete Basic Functionality Demonstration

Let's look at a more complete example that demonstrates context retention and multiple interactions:

```python
"""
Basic Example for AmritaCore - A simple demonstration of core functionality.

This example demonstrates how to initialize AmritaCore, configure it,
and run a basic chat session with the AI assistant.
"""

import asyncio

from amrita_core import ChatObject, init, load_amrita, logger
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig
from amrita_core.preset import PresetManager
from amrita_core.types import MemoryModel, Message, ModelConfig, ModelPreset


async def basic_example():
    """
    Basic example demonstrating core functionality of AmritaCore.
    Shows initialization, configuration, and a simple chat interaction.
    """
    print("🚀 Starting AmritaCore Basic Example")
    print("-" * 50)

    # Configure AmritaCore
    # FunctionConfig defines general behavior of the agent
    func = FunctionConfig(
        use_minimal_context=False,  # Use full context or minimal context
        tool_calling_mode="agent",  # How tools are called
        agent_thought_mode="reasoning",  # How agent thinks through problems
    )

    # LLMConfig defines language model behavior
    llm = LLMConfig(
        enable_memory_abstract=True,  # Enable memory abstraction feature
    )

    # Combine configs into main config
    config = AmritaConfig(
        function_config=func,
        llm=llm,
    )

    # Apply the configuration
    from amrita_core.config import set_config

    set_config(config)

    # Load AmritaCore components
    await load_amrita()

    # Setup model preset - define which LLM to use
    preset = ModelPreset(
        model="gpt-3.5-turbo",  # Model name
        base_url="INSERT_YOUR_API_ENDPOINT_HERE",  # API endpoint
        api_key="INSERT_YOUR_API_KEY_HERE",  # API key
        config=ModelConfig(stream=True),  # Enable streaming responses
    )

    # Register the model preset
    preset_manager = PresetManager()
    preset_manager.add_preset(preset)
    logger.info("✅ Registered model preset.")

    # Create a memory context to hold conversation history
    context = MemoryModel()

    # Define system instruction (how the AI should behave)
    train = Message(
        content="You are a helpful AI assistant. Answer concisely and accurately.",
        role="system",
    )

    print("💬 Starting a sample conversation:")
    print()

    # Example 1: Simple text interaction
    user_input = "Hello! Can you tell me what AmritaCore is?"

    print(f"👤 User: {user_input}")

    # Create a ChatObject for the interaction
    chat = ChatObject(
        context=context,
        session_id="basic_example_session",
        user_input=user_input,
        train=train.model_dump(),  # Convert Message to dictionary
    )

    # Process the response and display it
    print("🤖 Assistant: ", end="")

    # Start the chat processing
    await chat.call()

    # Print the streamed response
    async for message in chat.get_response_generator():
        content = message if isinstance(message, str) else message.get_content()
        print(content, end="")

    print("\n")  # New line after response

    # Update context with the latest conversation state
    context = chat.data

    # Example 2: Follow-up question to demonstrate context retention
    follow_up = "Can you explain its main features?"

    print(f"👤 User: {follow_up}")

    # Create another ChatObject with the updated context
    chat2 = ChatObject(
        context=context,
        session_id="basic_example_session",
        user_input=follow_up,
        train=train.model_dump(),
    )

    print("🤖 Assistant: ", end="")

    # Process the follow-up
    await chat2.call()

    async for message in chat2.get_response_generator():
        content = message if isinstance(message, str) else message.get_content()
        print(content, end="")

    print("\n")  # New line after response

    print("🎉 Basic example completed successfully!")
    print("-" * 50)
    print("💡 Key concepts demonstrated:")
    print("   • Initialization and configuration")
    print("   • Creating ChatObject instances")
    print("   • Streaming responses")
    print("   • Context management")
    print("   • Session handling")


async def minimal_example():
    """
    A minimal example showing the essential steps to run AmritaCore.
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

    # Run the chat
    await chat.call()

    # Collect response (just to show it works)
    response = await chat.full_response()
    print(f"💬 Response length: {len(response)} characters")
    print("✅ Minimal example completed!")


if __name__ == "__main__":
    # Initialize AmritaCore
    init()

    # Run examples
    asyncio.run(basic_example())
    asyncio.run(minimal_example())

    print("\n✨ All examples completed!")
```

## 2.3.2 Configuration Details

The example demonstrates several important configuration options:

- `use_minimal_context=False`: Uses full conversation history instead of just the last message
- `tool_calling_mode="agent"`: Configures how tools are invoked
- `agent_thought_mode="reasoning"`: Makes the agent think through problems before responding
- `enable_memory_abstract=True`: Enables automatic context summarization to manage token usage

## 2.3.3 Common Issue Troubleshooting

**Issue**: Connection errors to API endpoint
**Solution**: Verify your API endpoint and key are correct, and that you have network connectivity.

**Issue**: High token usage
**Solution**: Enable memory abstraction (`enable_memory_abstract=True`) and consider using minimal context mode for simpler queries.

**Issue**: Slow responses
**Solution**: Check your network connection and API provider performance. Consider using smaller models for faster responses.
