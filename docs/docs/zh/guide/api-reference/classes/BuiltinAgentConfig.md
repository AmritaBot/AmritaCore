# BuiltinAgentConfig

内置 ReAct 策略的配置。

## 属性

- `tool_calling_mode` (`Literal["agent", "rag", "none"]`)：默认 `"agent"`。Amrita 内置 agent 策略的工具调用模式
- `agent_thought_mode` (`Literal["reasoning", "chat", "reasoning-required", "reasoning-optional"]`)：默认 `"chat"`。思考模式：
  - `"reasoning"`——先执行推理过程，再执行任务
  - `"reasoning-required"`——每次工具调用都要求任务分析
  - `"reasoning-optional"`——不要求推理但允许推理
  - `"chat"`——直接执行，无推理步骤
- `loop_reasoning_trigger` (int)：默认 `5`，最小 `1`。容忍多少次重复的工具签名后才打断循环
- `react_config` ([ReactConfig](ReactConfig.md))：默认 `ReactConfig()`。ReAct 推理增强配置

## 描述

`BuiltinAgentConfig` 继承自 `BaseModel`，通过 `AmritaConfig.builtin` 公开。它配置内置 agent 策略的行为——使用哪种工具调用模式，以及停滞检测何时放弃。

工具调用进展与推理始终以结构化的 `function_call` / `reasoning_chunk` 事件流式输出。是否展示由消费者决定，因此这里没有开关：请改为过滤流（参见[流式与回调](../../tutorials/streaming.md)）。

## 示例

```python
from amrita_core.config import AmritaConfig, BuiltinAgentConfig, ReactConfig

config = AmritaConfig(
    builtin=BuiltinAgentConfig(
        tool_calling_mode="agent",
        agent_thought_mode="reasoning",
        agent_tool_call_notice="notify",
        loop_reasoning_trigger=3,
        react_config=ReactConfig(structured_reasoning=True),
    )
)
```

## 相关

- [ReactConfig](ReactConfig.md)——嵌套的推理增强配置
- [AmritaConfig](AmritaConfig.md)——父对象
- [ReActAgentStrategy](ReActAgentStrategy.md)——被本配置作用的策略
