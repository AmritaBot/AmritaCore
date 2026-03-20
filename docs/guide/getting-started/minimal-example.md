# Minimal Example

## 2.2.1 5-Minute Quick Start

Here's a minimal example to get you started with AmritaCore using the simplified `create_agent` function:

```python
import asyncio
from amrita_core import create_agent, minimal_init

async def minimal_example():
    # Initialize AmritaCore before creating agent
    await minimal_init()
    # Create an agent with minimal parameters
    agent = create_agent(
    "https://api.example.com", # Replace with your API URL
    "your-api-key", # Replace with your API key
    model="gpt-4", # Replace with your desired model
    model_config={"temperature": 0.7}
    )
    # Get a chat object for the interaction
    chat = agent.get_chatobject("Hello, what can you do?")

    # Execute the interaction and get the response
    async with chat.begin():
        print(await chat.full_response())

# Run the example
if __name__ == "__main__":
    asyncio.run(minimal_example())
```

## 2.2.2 Code Example Explanation

In this minimal example:

1. We use `minimal_init()` to initialize AmritaCore before creating the agent
2. We use `create_agent()` to create an agent with just the essential parameters (URL and API key)
3. The `create_agent` function automatically handles initialization, configuration, and preset creation
4. We call `agent.get_chatobject()` to get a `ChatObject` instance for our specific interaction
5. We execute the interaction using `chat.begin()` and get the full response

### Understanding ChatObject

`ChatObject` is the fine-grained standard interface in AmritaCore that provides complete control over individual chat interactions. While `create_agent` offers a high-level, simplified API for common use cases, `ChatObject` gives you access to all the underlying functionality including:

- Direct control over session management
- Custom context and memory handling
- Advanced configuration options
- Full access to the event system and hooks
- Detailed control over streaming behavior

For most basic use cases, `create_agent` is sufficient and much simpler to use. However, when you need fine-grained control or want to implement custom behavior, you can work directly with `ChatObject`.

## 2.2.3 Running and Debugging

To run the example:

1. Install AmritaCore
2. Replace `YOUR_API_ENDPOINT` and `YOUR_API_KEY` with actual values
3. Execute the script with `python your_script.py`

For debugging, you can enable verbose logging by configuring the logger in your code.
