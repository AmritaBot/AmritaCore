# Minimal Example

## 2.2.1 5-Minute Quick Start

Here's a minimal example to get you started with AmritaCore:

```python
import asyncio
from amrita_core import ChatObject, init, load_amrita
from amrita_core.config import AmritaConfig
from amrita_core.preset import PresetManager
from amrita_core.types import MemoryModel, Message, ModelConfig, ModelPreset

async def minimal_example():
    # Initialize AmritaCore
    init()
    
    # Set minimal configuration
    from amrita_core.config import set_config
    set_config(AmritaConfig())
    
    # Load AmritaCore components
    await load_amrita()
    
    # Create model preset
    preset = ModelPreset(
        model="gpt-3.5-turbo",
        base_url="YOUR_API_ENDPOINT",  # Replace with your API endpoint
        api_key="YOUR_API_KEY",        # Replace with your API key
        config=ModelConfig(stream=True)
    )
    
    # Register the model preset
    preset_manager = PresetManager()
    preset_manager.add_preset(preset)
    
    # Create context and system message
    context = MemoryModel()
    train = Message(content="You are a helpful assistant.", role="system")
    
    # Create and run a chat interaction
    chat = ChatObject(
        context=context,
        session_id="minimal_session",
        user_input="Hello, what can you do?",
        train=train.model_dump(),
    )

    async with chat.begin():
        print(await chat.get_full_response())

# Run the example
if __name__ == "__main__":
    asyncio.run(minimal_example())
```

## 2.2.2 Code Example Explanation

In this minimal example:

1. We initialize AmritaCore with `init()` which prepares internal components
2. We set a minimal configuration using `AmritaConfig()`
3. We load the core components with `load_amrita()`
4. We create a model preset defining which LLM to use
5. We register the preset with the PresetManager
6. We create a memory context and system message
7. We instantiate a ChatObject with our parameters
8. We call `chat.begin()` to execute the interaction
9. We get the response by use generator or `await chat.get_full_response()` (just use full response this will lose metadata.)
10. Finally, we get the full response

## 2.2.3 Running and Debugging

To run the example:

1. Install AmritaCore
2. Replace `YOUR_API_ENDPOINT` and `YOUR_API_KEY` with actual values
3. Execute the script with `python your_script.py`

For debugging, you can enable verbose logging by configuring the logger in your code.
