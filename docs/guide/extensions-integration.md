# Extensions and Integration

## 5.1 Extension Mechanisms

### 5.1.1 Tool System Extensions

AmritaCore provides a flexible way to extend its functionality through custom tools. You can create new tools that the agent can use to perform specific tasks:

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# First define the function schema
calculate_math_tool = FunctionDefinitionSchema(
    name="calculate_math",
    description="Calculate the result of a mathematical expression",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "expression": FunctionPropertySchema(
                type="string",
                description="Mathematical expression to evaluate"
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
    import re
    # Only allow numbers, operators, parentheses, and decimal points
    expression = data["expression"]
    if re.match(r'^[0-9+\-*/().\s]+$', expression):
        try:
            result = eval(expression)
            return str(float(result))  # Must return string!
        except Exception as e:
            return "0.0"
    else:
        return "Invalid expression"
```

### 5.1.2 Advanced Tool Patterns

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
    await ctx.event.chat_object.yield_response(f"{content}\n")

    # Return processed result
    return f"Sent a message to user:\n\n```text\n{content}\n```\n"
````

In custom run mode:

- The function receives a [ToolContext](../api-reference/classes/ToolContext.md) object instead of raw arguments
- The [ToolContext](../api-reference/classes/ToolContext.md) contains:
  - `ctx.data`: The arguments passed to the tool
  - `ctx.event`: The current event, allowing access to chat object
  - `ctx.matcher`: The matcher associated with the event
- Functions can be synchronous or asynchronous
- Return type can be `str` or `None`

### 5.1.2 Event Hook Extensions

Event hooks allow you to intercept and modify the processing pipeline:

```python
from amrita_core.hook.event import PreCompletionEvent, CompletionEvent
from amrita_core.hook.on import on_precompletion, on_completion
from amrita_core.types import Message

@on_precompletion()
async def inject_context(event: PreCompletionEvent):
    """Inject custom context before LLM processing"""
    event.messages.append(Message(
        role="system",
        content="Remember to be concise and helpful in your response."
    ))
    

@on_completion()
async def log_response(event: CompletionEvent):
    """Log the response after processing"""
    print(f"Response received: {event.response[:100]}...")
    
```

### 5.1.3 Protocol Adapters

Protocol adapters allow AmritaCore to work with different LLM providers or communication protocols:

```python
from amrita_core.protocol import ModelAdapter
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
        # Implementation for custom protocol
        # This should yield chunks of response as they arrive, then finally a UniResponse
        yield "response chunk"  # Yield response chunks as they arrive
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

## 5.3 Built-in Modules

### 5.3.1 builtins.adapter Adapter Module

The adapter module provides protocol adapters for different LLM providers:

```python
# Example of using a built-in adapter
from amrita_core.builtins import adapter

# Adapters are typically used internally by the framework
# But can be extended for custom integrations
from amrita_core.protocol import ModelAdapter
from amrita_core.types import ModelPreset
from collections.abc import AsyncGenerator, Iterable
from amrita_core.types import UniResponse

class MyCustomAdapter(ModelAdapter):

    async def call_api(
        self, messages: Iterable
    ) -> AsyncGenerator[str | UniResponse[str, None], None]:
        # Custom implementation
        yield "response chunk"
        yield UniResponse(
            role="assistant",
            content="Complete response",
            usage=None,
            tool_calls=None,
        )
        
    @staticmethod
    def get_adapter_protocol() -> str | tuple[str, ...]:
        return "my_custom_protocol"
```

### 5.3.2 builtins.agent Agent Module

The agent module contains core agent functionality:

```python
# Using built-in agent capabilities
from amrita_core.builtins.agent import Agent

# The agent module handles core agent behaviors like:
# - Tool selection and execution
# - Context management
# - Response generation
```

### 5.3.3 builtins.tools Tool Module

The built-in tools module provides standard tools:

```python
# Example of built-in tools (these are typically used automatically)
from amrita_core.builtins.tools import *

# Built-in tools might include:
# - Calculator
# - Web search
# - Date/time utilities
# - Unit conversion
```

### 5.3.4 Module Usage Guidelines

When using built-in modules:

1. Import what you need
2. Extend rather than replace functionality when possible
3. Follow the override pattern when replacing implementations
4. Maintain compatibility with the overall architecture

## 5.4 Custom Extension Development

### 5.4.1 Creating Custom Tools

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

### 5.4.2 Creating Custom Event Handlers

Build custom event handlers for specialized processing:

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion
from amrita_core.types import Message

@on_precompletion()
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

### 5.4.3 Creating Custom Protocol Adapters

Build adapters for different LLM providers:

```python
from amrita_core.protocol import ModelAdapter
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

### 5.4.4 Publishing and Sharing Extensions

To share your extensions:

1. Package them as a separate Python module
2. Document the functionality and usage
3. Publish to PyPI or host in a Git repository
4. Provide examples and best practices

## 5.5 Third-Party Integration

### 5.5.1 Common LLM Provider Integration

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

### 5.5.2 Database Connections

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

### 5.5.3 API Integration

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

### 5.5.4 Other Framework Integration

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

    chat = ChatObject(
        context=context,
        session_id=session_id,
        user_input=user_input,
        train=train.model_dump()
    )

    await chat.call()
    response = await chat.full_response()

    return {"response": response}
```

This section covers the various ways to extend and integrate AmritaCore with other systems, tools, and services. The framework's modular design makes it easy to add new functionality while maintaining compatibility with the core architecture.
