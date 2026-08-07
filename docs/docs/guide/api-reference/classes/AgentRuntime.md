# AgentRuntime

The AgentRuntime class is a high-level wrapper around ChatObject that provides a reusable agent operation interface.

This class encapsulates the complexity of ChatObject and provides a simplified API for agent interactions. It maintains session state, configuration, and strategy settings, making it a reusable object for multiple agent operations within the same context.

## Properties

- `strategy` (type[AgentStrategy]): Agent strategy class used for execution
- `session_id` (str): Session ID for the agent
- `slot` ([BackendSlots](BackendSlots.md)): Backend slots providing memory and ability backends
- `preset` (ModelPreset): Model preset configuration
- `config` (AmritaConfig): Amrita configuration object
- `train` (Message[str]): Training data (system prompts)
- `template` (Template): Jinja2 template used to render system role message

## Constructor Parameters

- `config` ([AmritaConfig](AmritaConfig.md)): Amrita configuration object containing global configuration settings
- `preset` ([ModelPreset](ModelPreset.md)): Model preset configuration defining basic model parameters and settings
- `train` (dict[str, str] | [Message](Message.md)[str]): System prompt for the agent (dict or Message object)
- `strategy` (type[AgentStrategy], optional): Agent strategy class, defaults to ReActAgentStrategy
- `template` (Template | str, optional): Jinja2 template used to render the system prompt, defaults to DEFAULT_TEMPLATE
- `session_id` (str | None, optional): Session identifier string. If None, a new UUID-based ID is generated. The session_id is passed to every ChatObject created by this runtime, allowing the Backend to isolate memory and abilities per session
- `backend` ([BackendSlots](BackendSlots.md) | None, optional): Backend slots providing memory and ability backends. If None, a `LegacyBackend` is used for both slots, which stores data in global in-process containers

## Methods

### set_strategy(strategy)

Set the agent strategy to be used for execution.

**Parameters**:

- `strategy` (type[AgentStrategy]): The agent strategy to be used for execution

### get_chatobject(input, \*\*kwargs)

Get a chat object for a specific interaction.

**Parameters**:

- `input` (USER_INPUT): Input from the user
- `**kwargs`: Additional keyword arguments passed to ChatObject constructor

**Returns**: [ChatObject](ChatObject.md) - A configured ChatObject instance ready for execution

## Usage Example

```python
from amrita_core import create_agent

# Create an agent using the factory function
agent = create_agent(
    "https://api.example.com",
    "your-api-key",
    model="gpt-4",
    model_config={"temperature": 0.7},
)

# Get a chat object for interaction
chat = agent.get_chatobject("Hello, what can you do?")

# Execute the interaction
async with chat.begin():
    response = await chat.full_response()
    await chat  # Wait for the task to finish before exiting
    print(response)
```
