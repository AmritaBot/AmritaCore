# AmritaConfig

The AmritaConfig class is the central configuration object for AmritaCore.

## Properties

- `function_config` ([FunctionConfig](FunctionConfig.md)): Functional behavior configuration
- `llm` ([LLMConfig](LLMConfig.md)): Language model configuration
- `cookie` ([CookieConfig.md](CookieConfig.md)): Security configuration

## Example

```python
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig, CookieConfig

config = AmritaConfig(
    function_config=FunctionConfig(
        use_minimal_context=False,
        tool_calling_mode="agent"
    ),
    llm=LLMConfig(
        enable_memory_abstract=True
    ),
    cookie=CookieConfig(
        enable_cookie=True
    )
)
```

## Description

The AmritaConfig class inherits from BaseModel and contains the main configuration options for the AmritaCore framework, divided into three parts:

1. Function configuration: Controls the behavior of the framework
2. LLM configuration: Controls parameters and behaviors of the language model
3. Cookie configuration: Controls security-related settings
