# Extensions and Integration

## 5.1 Extension Mechanisms

### 5.1.1 Simple Tools

AmritaCore provides a simple way to extend its functionality through simple tools:

```python
from amrita_core import simple_tool

@simple_tool
def add(a: int, b: int) -> int:
    """Add two numbers

    Args:
        a (int): First number
        b (int): Second number

    Returns:
        int: Sum of a and b
    """
    return a + b
```

This tool will be automatically registered and available to the agent.

In the `__doc__` block(Always is `"""` block) of the tool, you can add a description and parameters for the tool as Google's format. The parameters will be used to describe the parameters for LLM when the tool is called.

**Registration Scope**: Tools registered with `@simple_tool` are added to the global container during module loading and are available to all sessions.

**Supported Types**: The `@simple_tool` decorator now supports rich type annotations including Pydantic models, List[T], and Optional[T]. See the [Tool System](../concepts/tool.md) documentation for complete type support details.

### 5.1.2 Tool System Extensions

AmritaCore provides a flexible way to extend its functionality through custom tools. You can create new tools that the agent can use to perform specific tasks:

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# First define the function schema with advanced validation
calculate_math_tool = FunctionDefinitionSchema(
    name="calculate_math",
    description="Calculate the result of a mathematical expression",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "expression": FunctionPropertySchema(
                type="string",
                description="Mathematical expression to evaluate",
                minLength=1,
                maxLength=1000,
                pattern=r"^[0-9+\-*/().\s]+$"  # Only allow safe math characters
            ),
            "precision": FunctionPropertySchema(
                type="integer",
                description="Number of decimal places for result",
                minimum=0,
                maximum=10,
                default=2
            )
        },
        required=["expression"]
    )
)

@on_tools(data=calculate_math_tool)
async def calculate_math(data: dict) -> str:
    """
    Calculate the result of a mathematical expression
    """
    # In a real implementation, you'd want to use a safe eval method
    # or a dedicated math library to prevent code injection
    expression = data["expression"]
    precision = data.get("precision", 2)

    # The pattern validation ensures only safe characters are present
    try:
        result = eval(expression)
        return f"{float(result):.{precision}f}"  # Must return string!
    except Exception as e:
        return "0.0"
```

**Registration Scope**: Like `@simple_tool`, the `@on_tools` decorator registers tools to the global container during module loading.

### Enhanced Validation Features

`FunctionPropertySchema` supports comprehensive JSON Schema validation with type-specific constraints:

- **Numeric Constraints**: `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`
- **String Constraints**: `minLength`, `maxLength`, `pattern`, `format`
- **Array Constraints**: `items`, `minItems`, `maxItems`, `uniqueItems`
- **Object Constraints**: `properties`, `required`, `additionalProperties`
- **Special Values**: `enum`, `const`, `default`
- **Union Types**: `type` can be a list of allowed types (only available with manual schema definition, not through `@simple_tool`)

These constraints are automatically validated when the LLM generates tool calls, ensuring that only valid parameter values are passed to your tool functions.

> **Note on Registration Methods**:
>
> - **Decorators** (`@simple_tool`, `@on_tools`): Register to global container at module load time, available to all sessions
> - **Direct Manager Operations**: Allow session-specific tool management at runtime using `ToolsManager` or `MultiToolsManager` instances

### 5.1.3 Advanced Tool Patterns

For tools that require access to the event context or more advanced processing, you can use the `custom_run` mode:

````python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema, ToolContext
from amrita_core.logging import logger

# Define the function schema
process_message_tool = FunctionDefinitionSchema(
    name="processing_message",
    description="Describe what the agent is currently doing and express the agent's internal thoughts to the user",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "content": FunctionPropertySchema(
                type="string",
                description="Message content describing current actions"
            )
        },
        required=["content"]
    )
)

@on_tools(data=process_message_tool, custom_run=True)
async def process_message(ctx: ToolContext) -> str | None:
    """
    Process a message and send it to the user via the chat object
    """
    content = ctx.data["content"]
    logger.debug(f"[LLM-ProcessMessage] {content}")

    # Send message directly to the chat object
    await ctx.ctx.chat_object.yield_response(f"{content}\n")

    # Return processed result
    return f"Sent a message to user:\n\n```text\n{content}\n```\n"
````

In custom run mode:

- The function receives a [ToolContext](../api-reference/classes/ToolContext.md) object instead of raw arguments
- The [ToolContext](../api-reference/classes/ToolContext.md) contains:
  - `ctx.data`: The arguments passed to the tool
  - `ctx.ctx`: The [StrategyContext](../api-reference/classes/StrategyContext.md) containing the current execution context, including access to the chat object
- Functions can be synchronous or asynchronous
- Return type can be `str` or `None`

### 5.1.4 Event Hook Extensions

Event hooks allow you to intercept and modify the processing pipeline:

```python
from amrita_core.hook.event import PreCompletionEvent, CompletionEvent
from amrita_core.hook.on import on_precompletion, on_completion
from amrita_core.types import Message

@on_precompletion().handle()
async def inject_context(event: PreCompletionEvent):
    """Inject custom context before LLM processing"""
    event.messages.append(Message(
        role="system",
        content="Remember to be concise and helpful in your response."
    ))


@on_completion().handle()
async def log_response(event: CompletionEvent):
    """Log the response after processing"""
    print(f"Response received: {event.response[:100]}...")

```

### 5.1.5 Protocol Adapters & Custom Tokenizers

Protocol adapters allow AmritaCore to work with different LLM providers or communication protocols. Tokenizers handle text tokenization for memory management and context windows.

Both adapters and tokenizers support **two registration mechanisms**:

#### Mechanism 1: Implicit Registration via Subclassing (Anywhere)

Subclass `ModelAdapter` or `BaseTokenizer` anywhere in your codebase — the `__init_subclass__` hook automatically registers the class in the corresponding manager (`AdapterManager` or `TokenizerManager`) when the module is imported.

```python
# my_project/adapters.py
from amrita_core.base.adapter import ModelAdapter
from amrita_core.base.tokenizer import BaseTokenizer
from amrita_core.types import ModelPreset

class MyCustomAdapter(ModelAdapter):
    # Manually import this module to trigger registration
    ...

class MyCustomTokenizer(BaseTokenizer):
    # Manually import this module to trigger registration
    ...
```

Then explicitly import to trigger registration:

```python
import my_project.adapters  # Triggers __init_subclass__ registration
```

#### Mechanism 2: Namespace Package Auto-Discovery (Recommended for Built-in Style)

AmritaCore uses Python's **namespace package** mechanism (PEP 420) to auto-discover adapters and tokenizers at startup. Simply place your file in the `adapters/` or `tokenizers/` directory **without an `__init__.py`** — the directory becomes a namespace package, and `side_effect_import` (called during `amrita_core` import) discovers and imports all submodules automatically.

```
src/amrita_core/
├── adapters/          # ← MUST NOT have __init__.py
│   ├── openai.py      # Auto-discovered
│   ├── anthropic.py   # Auto-discovered
│   └── my_adapter.py  # ← Your custom adapter
├── tokenizers/        # ← MUST NOT have __init__.py
│   ├── simple.py      # Auto-discovered
│   └── my_tokenizer.py # ← Your custom tokenizer
```

**What happens at import time:**

1. `import amrita_core` runs `side_effect_import(adapters)` and `side_effect_import(tokenizers)`
2. These scan the namespace package directories for all `.py` files (via `pkgutil.iter_modules`)
3. Each discovered module is imported, which triggers the `__init_subclass__` hook in `ModelAdapter` / `BaseTokenizer`
4. The class is automatically registered in `AdapterManager` / `TokenizerManager`

**Critical rule**: The `adapters/` and `tokenizers/` directories **must NOT contain `__init__.py`**. An `__init__.py` would turn them into regular packages, breaking the namespace package auto-discovery mechanism.

#### Example: Creating an Adapter

```python
# src/amrita_core/adapters/custom_protocol.py
from amrita_core.base.adapter import ModelAdapter
from amrita_core.types import ModelPreset
from collections.abc import AsyncGenerator, Iterable
from amrita_core.types import UniResponse

class CustomAdapter(ModelAdapter):
    def __init__(self, preset: ModelPreset):
        super().__init__(preset=preset)
        self.__override__ = True  # Allow overriding existing adapters

    async def call_api(
        self, messages: Iterable
    ) -> AsyncGenerator[str | UniResponse[str, None], None]:
        # Yield response chunks as they arrive, then finally a UniResponse
        yield "response chunk"
        yield UniResponse(
            role="assistant",
            content="Complete response",
            usage=None,
            tool_calls=None,
        )

    @staticmethod
    def get_adapter_protocol() -> str | tuple[str, ...]:
        return "custom_protocol"  # Return the protocol name
```

## 5.2 MCP Client Integration

### 5.2.1 What is MCP?

Model Context Protocol (MCP) is a standard for connecting tools and data sources to AI models. It allows models to interact with external systems in a structured way, extending their capabilities beyond their training data.

### 5.2.2 mcp.ClientManager MCP Client Management

The [ClientManager](../api-reference/classes/ClientManager.md) class manages MCP client connections:

```python
from amrita_core.tools import mcp

# Initialize MCP clients for a session
async def setup_mcp_clients():
    client_manager = mcp.ClientManager()
    scripts = [
        "/path/to/script1.mcp",
        "/path/to/script2.mcp"
    ]
    await client_manager.initialize_scripts_all(scripts)
```

### 5.2.3 MCP Script Configuration

Configure MCP scripts in your settings:

```python
from amrita_core.config import AmritaConfig, FunctionConfig

config = AmritaConfig(
    function_config=FunctionConfig(
        agent_mcp_client_enable=True,
        agent_mcp_server_scripts=[
            "./mcp-scripts/weather.mcp",
            "./mcp-scripts/database.mcp",
            "./mcp-scripts/calendar.mcp"
        ]
    )
)
```

### 5.2.4 MCP Practical Examples

Real-world MCP use cases:

1. **Database Access**: Querying databases through MCP clients
2. **File System Operations**: Reading/writing files securely
3. **API Integration**: Connecting to third-party APIs
4. **IoT Devices**: Interfacing with physical devices

For detailed information about MCP server integration, architecture, and how to create your own MCP servers, see [MCP Server Integration](./mcp-server-integration.md).

## 5.3 Custom Extension Development

### 5.3.1 Creating Custom Tools

Develop custom tools for specific functionality:

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema
from typing import Dict, Any
import json

# Define the function schema for translation
translate_tool = FunctionDefinitionSchema(
    name="translate_text",
    description="Translate text to a target language",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "text": FunctionPropertySchema(
                type="string",
                description="Text to translate"
            ),
            "target_language": FunctionPropertySchema(
                type="string",
                description="Target language code (default: en)",
                default="en"
            )
        },
        required=["text"]
    )
)

@on_tools(data=translate_tool)
async def translate_text(data: dict) -> str:
    """
    Translate text to a target language
    """
    text = data["text"]
    target_language = data.get("target_language", "en")
    # In a real implementation, connect to a translation API
    # For this example, we'll simulate the translation
    simulated_translation = f"[TRANSLATED TO {target_language.upper()}]: {text}"
    return simulated_translation

# Define the function schema for getting company info
company_info_tool = FunctionDefinitionSchema(
    name="get_company_info",
    description="Get information about a company",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "company_name": FunctionPropertySchema(
                type="string",
                description="Name of the company to look up"
            )
        },
        required=["company_name"]
    )
)

@on_tools(data=company_info_tool)
async def get_company_info(data: dict) -> str:
    """
    Get information about a company
    """
    company_name = data["company_name"]
    # This would connect to a database or API in a real implementation
    result = {
        "name": company_name,
        "status": "simulated",
        "info": f"Information about {company_name}"
    }
    return json.dumps(result)
```

### 5.3.2 Creating Custom Event Handlers

Build custom event handlers for specialized processing:

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion
from amrita_core.types import Message

@on_precompletion().handle()
async def security_check(event: PreCompletionEvent):
    """
    Perform security checks before processing
    """
    # Check for potentially harmful content
    for msg in event.messages:
        if msg.role == "user":
            # Implement security checks here
            if "harmful" in msg.content.lower():
                # Modify the message to include a warning
                event.messages.append(Message(
                    role="system",
                    content="Content filtered for safety"
                ))


```

### 5.3.3 Creating Custom Protocol Adapters

Build adapters for different LLM providers. See [5.1.5 Protocol Adapters & Custom Tokenizers](#515-protocol-adapters--custom-tokenizers) for the two registration mechanisms (implicit subclassing and namespace package auto-discovery).

```python
from amrita_core.base.adapter import ModelAdapter
from amrita_core.types import ModelPreset, UniResponse
from collections.abc import AsyncGenerator, Iterable
import aiohttp

class CustomLLMAdapter(ModelAdapter):
    def __init__(self, preset: ModelPreset):
        super().__init__(preset=preset)
        self.__override__ = True  # Allow this to override existing registrations

    async def call_api(
        self, messages: Iterable
    ) -> AsyncGenerator[str | UniResponse[str, None], None]:
        """
        Make a call to the custom LLM API
        """
        headers = {
            'Authorization': f'Bearer {self.preset.api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'messages': list(messages),
            'model': self.preset.model,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.preset.base_url}/chat/completions",
                                   json=payload, headers=headers) as response:
                result = await response.json()

                # Yield response chunks as they arrive (for streaming)
                # For simplicity in this example, we'll yield the full response

                content = result['choices'][0]['message']['content']
                yield content  # This yields the content chunk by chunk

                # Finally, yield the complete UniResponse
                yield UniResponse(
                    role="assistant",
                    content=content,
                    usage=result.get('usage', {}),
                    tool_calls=None,
                )

    @staticmethod
    def get_adapter_protocol() -> str | tuple[str, ...]:
        return "custom_llm_protocol"  # Return the protocol identifier
```

### 5.3.4 Package Naming Convention & Publishing

To maintain ecosystem consistency, use the following naming prefix when publishing AmritaCore extensions to PyPI:

| Extension Type | Package Name Prefix  | Example                      |
| -------------- | -------------------- | ---------------------------- |
| **Adapter**    | `amcore-adapter-*`   | `amcore-adapter-grok`        |
| **Tokenizer**  | `amcore-tokenizer-*` | `amcore-tokenizer-bert`      |
| **Strategy**   | `amcore-strategy-*`  | `amcore-strategy-reflection` |
| **Hook/Event** | `amcore-hook-*`      | `amcore-hook-rate-limiter`   |
| **Tool**       | `amcore-tool-*`      | `amcore-tool-calculator`     |

To publish and share your extensions:

1. Package as a separate Python module following the naming convention above
2. Add relevant classifiers in `pyproject.toml`, e.g. `Framework :: AmritaCore`
3. Document functionality, usage examples, and dependencies
4. Publish to PyPI or host in a Git repository

## 5.4 Third-Party Integration

### 5.4.1 Common LLM Provider Integration

Integrate with various LLM providers:

```python
# OpenAI-compatible endpoint
from amrita_core.types import ModelPreset, ModelConfig

openai_preset = ModelPreset(
    model="gpt-4",
    base_url="https://api.openai.com/v1",
    api_key="your-openai-api-key",
    config=ModelConfig(stream=True)
)

# Azure OpenAI
azure_preset = ModelPreset(
    model="your-deployment-name",
    base_url="https://your-resource.openai.azure.com",
    api_key="your-azure-api-key",
    config=ModelConfig(stream=True)
)
```

### 5.4.2 Database Connections

Connect to databases using tools:

```python
import sqlite3
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# Define the function schema
query_db_tool = FunctionDefinitionSchema(
    name="query_database",
    description="Query a SQLite database",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "query": FunctionPropertySchema(
                type="string",
                description="SQL query to execute"
            )
        },
        required=["query"]
    )
)

@on_tools(data=query_db_tool)
async def query_database(data: dict) -> str:
    """
    Query a SQLite database
    """
    query = data["query"]
    try:
        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return str(results)
    except Exception as e:
        return f"Error executing query: {str(e)}"
```

### 5.4.3 API Integration

Integrate with external APIs:

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema
import aiohttp

# Define the function schema
get_weather_tool = FunctionDefinitionSchema(
    name="get_weather_data",
    description="Get weather data from an external API",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "city": FunctionPropertySchema(
                type="string",
                description="City to get weather for"
            )
        },
        required=["city"]
    )
)

@on_tools(data=get_weather_tool)
async def get_weather_data(data: dict) -> str:
    """
    Get weather data from an external API
    """
    city = data["city"]
    api_key = "your-weather-api-key"
    url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return f"Weather in {city}: {data['current']['condition']['text']}, {data['current']['temp_c']}°C"
            else:
                return f"Could not retrieve weather for {city}"
```

### 5.4.3 Other Framework Integration

Combine AmritaCore with other frameworks:

```python
# Example: Integration with FastAPI for a web service
from fastapi import FastAPI
from amrita_core import ChatObject, init
from amrita_core.config import AmritaConfig
from amrita_core.types import MemoryModel, Message

app = FastAPI()

# Initialize AmritaCore when the app starts
init()
from amrita_core.config import set_config
set_config(AmritaConfig())

@app.post("/chat/")
async def chat_endpoint(user_input: str, session_id: str):
    context = MemoryModel()
    train = Message(content="You are a helpful assistant.", role="system")

    async with ChatObject(
        context=context,
        session_id=session_id,
        user_input=user_input,
        train=train.model_dump()
    ).begin() as chat:
        response = await chat.full_response()

    return {"response": response}
```

This section covers the various ways to extend and integrate AmritaCore with other systems, tools, and services. The framework's modular design makes it easy to add new functionality while maintaining compatibility with the core architecture.
