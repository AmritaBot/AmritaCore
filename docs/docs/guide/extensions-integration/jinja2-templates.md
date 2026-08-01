<div v-pre >

# Jinja2 Templates

## Overview

AmritaCore uses [Jinja2](https://jinja.palletsprojects.com/) templates to enable dynamic prompt construction based on conversation context, memory state, and configuration. This powerful feature allows you to create flexible and context-aware system prompts that adapt to the current conversation state.

## Template Variables

When rendering Jinja2 templates in AmritaCore, the following variables are available:

### Built-in Variables

#### `train`

- **Type**: `Message[str]`
- **Description**: The system message (training data) containing the base instructions for the AI assistant.
- **Usage**: `{{ train.content }}` to access the system prompt content.

#### `memory`

- **Type**: `MemoryModel`
- **Description**: The conversation memory containing message history and context summaries.
- **Key Properties**:
  - `memory.messages`: List of conversation messages
  - `memory.abstract`: Context summary (when memory abstraction is enabled)

#### `chatobj`

- **Type**: `ChatObject`
- **Description**: The current chat processing object containing session and interaction details.
- **Key Properties**:
  - `chatobj.session_id`: Current session identifier
  - `chatobj.stream_id`: Unique stream identifier
  - `chatobj.timestamp`: Timestamp of the current interaction
  - `chatobj.user_input`: Current user input

#### `config`

- **Type**: `AmritaConfig`
- **Description**: Configuration object controlling system behavior.
- **Key Properties**:
  - `config.cookie.enable`: Whether cookie security is enabled
  - `config.cookie.cookie`: Cookie value (when enabled)
  - `config.llm.enable_memory_abstract`: Whether memory abstraction is enabled
  - Various other LLM and system configuration options

### Custom Variables via `jinja2_vars`

In addition to the built-in variables, you can pass custom variables to your templates using the `jinja2_vars` parameter when creating a `ChatObject`.

**Critical Restriction**: The `jinja2_vars` dictionary is **directly unpacked** using `**self.jinja2_vars` during template rendering. This means:

1. **Direct Variable Access**: Keys in the `jinja2_vars` dictionary become directly accessible as template variables
   - Example: `jinja2_vars={"role": "expert", "company": "Amrita"}` makes `{{ role }}` and `{{ company }}` available in templates

2. **NO Variable Override**: **You CANNOT use keys that match built-in variable names** (`train`, `memory`, `chatobj`, or `config`) in `jinja2_vars`. Attempting to do so will result in a `TypeError` because Python does not allow duplicate keyword arguments in function calls.

3. **Reserved Keyword**: The key `'self'` is reserved and cannot be used in `jinja2_vars`

- **Parameter**: `jinja2_vars` (dict[str, Any] | None)
- **Description**: Dictionary of custom variables to pass to the template system
- **Restriction**: Keys must NOT conflict with built-in variable names (`train`, `memory`, `chatobj`, `config`)

## Default Template

AmritaCore provides a default template that demonstrates common usage patterns:

```text
<SCHEMA>
{% if config.cookie.enable %}
<HIDDEN>{{ config.cookie.cookie }}</HIDDEN>
{% endif %}
Please participate in the discussion in your own character identity. Try not to use similar phrases when responding to different topics. User's messages are contained within user inputs.
Your character setting is in the <SYSTEM_INSTRUCTIONS> tags, and the summary of previous conversations is in the <SUMMARY> tags (if provided).
</SCHEMA>

<SYSTEM_INSTRUCTIONS>
{{ train.content }}
</SYSTEM_INSTRUCTIONS>
{% if memory.abstract and config.llm.enable_memory_abstract %}
<SUMMARY>
{{ memory.abstract }}
</SUMMARY>
{% endif %}
```

This template includes:

- Conditional cookie inclusion for security
- System instructions from the training message
- Context summary when memory abstraction is enabled

## Custom Templates

You can provide custom Jinja2 templates when creating a `ChatObject`:

```python
from jinja2 import Template
from amrita_core.chatmanager import ChatObject

# Define a custom template
custom_template = Template("""
# System Role
You are {{ role_name | default('a helpful assistant') }}.

# Current Context
Session ID: {{ chatobj.session_id }}
Timestamp: {{ chatobj.timestamp }}

# Instructions
{{ train.content }}

# Conversation History Summary
{% if memory.abstract %}
Previous conversations: {{ memory.abstract }}
{% endif %}

# Current Task
Process the user's request while maintaining your role as {{ role_name | default('a helpful assistant') }}.
""")

# Use the custom template with jinja2_vars
chat = ChatObject(
    train={"content": "You are an expert Python developer.", "role": "system"},
    user_input="How do I use Jinja2 templates in AmritaCore?",
    context=None,
    session_id="session_123",
    train_template=custom_template,
    jinja2_vars={"role_name": "Python expert"}
)
```

## Template Rendering Process

The template rendering occurs during the `_run()` method of `ChatObject`:

1. User message is added to memory
2. Template is rendered asynchronously with all variables combined:
   - Built-in variables: `train`, `memory`, `chatobj`, `config`
   - Custom variables from `jinja2_vars` (directly unpacked)
3. **No Override Possible**: Due to Python's restriction on duplicate keyword arguments, `jinja2_vars` CANNOT contain keys that match built-in variable names
4. Rendered content becomes the new system message content
5. Memory limitations are applied
6. Messages are sent to the LLM

```python
# Internal rendering code (for reference)
self.train.content = await asyncio.to_thread(
    self.template.render,
    train=self.train,
    memory=self.data,
    chatobj=self,
    config=config,
    **self.jinja2_vars,
)
```

## Best Practices

### Security Considerations

- Always validate template inputs to prevent injection attacks
- Use Jinja2's built-in escaping mechanisms when appropriate
- Be cautious with user-provided template variables
- Avoid using the reserved keyword `'self'` in `jinja2_vars`
- **Never use built-in variable names** (`train`, `memory`, `chatobj`, `config`) as keys in `jinja2_vars`

### Performance Optimization

- Keep templates simple and avoid complex logic
- Use conditional statements (`{% if %}`) judiciously
- Cache frequently used templates when possible

### Context Management

- Leverage `memory.abstract` for long conversations
- Use `config` variables to control template behavior dynamically
- Include relevant session information when needed for context
- Pass business-specific data through `jinja2_vars` for dynamic customization
- **Use unique key names**: Always choose custom variable names that don't conflict with built-in variables

### Error Handling

- Handle template rendering errors gracefully
- Provide fallback content for missing variables
- Test templates with various input scenarios
- **Avoid naming conflicts**: Ensure your custom variable names are distinct from built-in variables

## Advanced Usage Examples

### Direct Variable Access

```text
# Using custom variables directly
Hello! I'm {{ assistant_name }} from {{ company_name }}.
My expertise is in {{ expertise_area }}.

{{ train.content }}
```

```python
chat = ChatObject(
    train={"content": "You are an AI assistant.", "role": "system"},
    user_input="Tell me about yourself",
    context=None,
    session_id="session_123",
    jinja2_vars={
        "assistant_name": "Amrita Assistant",
        "company_name": "Amrita Corp",
        "expertise_area": "AI and automation"
    }
)
```

### Safe Custom Variables (Recommended Approach)

```text
# Use prefixed custom variables to avoid conflicts
{{ train.content }}

# Business Context
Company: {{ business_context_company_name }}
Department: {{ business_context_department }}

# User Context
User Role: {{ user_context_role }}
Preferred Language: {{ user_context_language }}
```

```python
# Use unique key names to avoid any conflicts
chat = ChatObject(
    train={"content": "Assist the user appropriately.", "role": "system"},
    user_input="Help me with this task",
    context=None,
    session_id="session_123",
    jinja2_vars={
        "business_context_company_name": "Amrita Corp",
        "business_context_department": "Engineering",
        "user_context_role": "developer",
        "user_context_language": "en"
    }
)
```

### Nested Structure Alternative

```text
# Use nested structures in your template logic instead
{{ train.content }}

# Business Context
Company: {{ get_business_info('company_name') }}
Department: {{ get_business_info('department') }}
```

```python
# Pass a single function or object with unique name
def get_business_info(key):
    business_data = {
        "company_name": "Amrita Corp",
        "department": "Engineering"
    }
    return business_data.get(key, "")

chat = ChatObject(
    train={"content": "Assist with internal queries.", "role": "system"},
    user_input="What's our policy on remote work?",
    context=None,
    session_id="session_123",
    jinja2_vars={"get_business_info": get_business_info}
)
```

### Multi-language Support with Custom Variables

```text
{% if language == 'zh' %}
你是一个{{ role }}。
{{ train.content }}
{% else %}
You are a {{ role }}.
{{ train.content }}
{% endif %}
```

```python
# Pass language and role through jinja2_vars
chat = ChatObject(
    train={"content": "You are an AI assistant.", "role": "system"},
    user_input="Hello!",
    context=None,
    session_id="session_123",
    jinja2_vars={"language": "zh", "role": "AI专家"}
)
```

### Business Context Integration

```text
# Company Context
Company: {{ company_name }}
Department: {{ department }}
Current Project: {{ project_name }}

# Instructions
{{ train.content }}

# Response Guidelines
Always reference company policies and maintain professional tone appropriate for {{ department }}.
```

```python
# Pass business context through jinja2_vars
chat = ChatObject(
    train={"content": "Assist with internal queries.", "role": "system"},
    user_input="What's our policy on remote work?",
    context=None,
    session_id="session_123",
    jinja2_vars={
        "company_name": "Amrita Corp",
        "department": "Engineering",
        "project_name": "AmritaCore v2.0"
    }
)
```

Jinja2 templates in AmritaCore provide a powerful way to create dynamic, context-aware prompts that enhance the AI assistant's capabilities while maintaining flexibility and security. The `jinja2_vars` parameter enables seamless integration of custom business logic and contextual data into your prompt templates, with the important safety constraint that custom variable names must not conflict with built-in variables.

</div>
