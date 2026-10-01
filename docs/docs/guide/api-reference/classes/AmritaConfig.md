# AmritaConfig

The AmritaConfig class is the central configuration object for AmritaCore.

## Properties

- `function_config` ([FunctionConfig](FunctionConfig.md)): Functional behavior configuration
- `llm` ([LLMConfig](LLMConfig.md)): Language model configuration
- `cookie` (`CookieConfig`): Security configuration
- `builtin` (`BuiltinAgentConfig`): Built-in agent configuration

## Example

```python
from amrita_core.config import (
    AmritaConfig,
    FunctionConfig,
    LLMConfig,
    CookieConfig,
    BuiltinAgentConfig,
)

config = AmritaConfig(
    function_config=FunctionConfig(use_minimal_context=False),
    llm=LLMConfig(enable_compaction=True),
    cookie=CookieConfig(enable_cookie=True),
    builtin=BuiltinAgentConfig(tool_calling_mode="agent"),
)
```

## Description

The AmritaConfig class inherits from BaseModel and contains the main configuration options for the AmritaCore framework, divided into four parts:

1. Function configuration: Controls the behavior of the framework
2. LLM configuration: Controls parameters and behaviors of the language model
3. Cookie configuration: Controls security-related settings
4. Built-in agent configuration: Controls the built-in ReAct strategy
