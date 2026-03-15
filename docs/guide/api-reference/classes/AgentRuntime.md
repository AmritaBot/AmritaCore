# AgentRuntime

The AgentRuntime class is a high-level wrapper around ChatObject that provides a reusable agent operation interface.

This class encapsulates the complexity of ChatObject and provides a simplified API for agent interactions. It maintains session state, configuration, and strategy settings, making it a reusable object for multiple agent operations within the same context.

## Properties

- `strategy` (type[AgentStrategy]): Agent strategy class used for execution
- `session_id` (str): Session ID for the agent
- `session` (SessionData | None): Session data or None if no session
- `preset` (ModelPreset): Model preset configuration
- `config` (AmritaConfig): Amrita configuration object
- `train` (Message[str]): Training data (system prompts)
- `context` (MemoryModel): Memory context for the conversation
- `template` (Template): Jinja2 template used to render system role message

## Constructor Parameters

- `config` ([AmritaConfig](AmritaConfig.md)): Amrita configuration object containing global configuration settings
- `preset` ([ModelPreset](ModelPreset.md)): Model preset configuration defining basic model parameters and settings
- `strategy` (type[AgentStrategy], optional): Agent strategy class, defaults to AmritaAgentStrategy
- `template` (Template | str, optional): Train template to render system role message, defaults to DEFAULT_TEMPLATE
- `session` (SessionData | str | None, optional): Session data or session ID string for restoring existing sessions. If None, a new session will be created
- `train` (dict[str, str] | Message[str] | None, optional): Training data (system prompts), can be in dictionary format or as a Message object
- `no_session` (bool, optional): Whether to disable session functionality. If True, session management will be disabled but a temporary session ID will still be assigned

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
    model_config={"temperature": 0.7}
)

# Get a chat object for interaction
chat = agent.get_chatobject("Hello, what can you do?")

# Execute the interaction
async with chat.begin():
    response = await chat.full_response()
    print(response)
```
