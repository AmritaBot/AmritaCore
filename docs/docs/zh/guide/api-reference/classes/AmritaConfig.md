# AmritaConfig

AmritaConfig 类是 AmritaCore 的中央配置对象。

## 属性

- `function_config` ([FunctionConfig](FunctionConfig.md))：功能行为配置
- `llm` ([LLMConfig](LLMConfig.md))：语言模型配置
- `cookie` (`CookieConfig`)：安全配置
- `builtin` (`BuiltinAgentConfig`)：内置 agent 配置

## 示例

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
    llm=LLMConfig(context_strategy="compact"),
    cookie=CookieConfig(enable_cookie=True),
    builtin=BuiltinAgentConfig(tool_calling_mode="agent"),
)
```

## 描述

AmritaConfig 类继承自 BaseModel，包含 AmritaCore 框架的主要配置选项，分为四个部分：

1. 功能配置：控制框架的行为
2. LLM 配置：控制语言模型的参数和行为
3. Cookie 配置：控制安全相关设置
4. 内置 agent 配置：控制内置 ReAct 策略
