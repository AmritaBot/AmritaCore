# ReactConfig

ReAct agent 的推理增强配置。

## 描述

`ReactConfig` 通过结构化思维链分解、推理后自我反思，以及推理感知的工具选择，逐步增强内置 ReAct agent 的推理能力。它通过 `AmritaConfig.builtin.react_config` 公开。

**所有选项默认关闭**以保持向后兼容：什么都不启用即复现普通 ReAct 循环。

## 属性

### 结构化推理

- `structured_reasoning` (bool)：默认 `False`。启用带显式阶段标记（analyze / plan / execute / verify）的逐步结构化推理。为 `True` 时，推理模板引导模型把问题分解为编号步骤
- `reasoning_depth` (int)：默认 `3`，范围 `1..10`。推理链最大深度（子问题数量）。在结构化推理模板中作为软性提示

### 自我反思

- `enable_reflection` (bool)：默认 `False`。在 `STOP_TOOL` 之后调用 `verify_reasoning` 工具，检查矛盾、完整性与对用户目标的对齐情况，然后再生成最终答案
- `reflection_depth` (int)：默认 `1`，范围 `1..5`。最大反思轮数。每轮可能产出一个修正，反馈回推理循环

### 推理感知的工具选择

- `reasoning_aware_tools` (bool)：默认 `False`。把结构化推理期间预测到的工具排在工具列表前面，把模型推向最相关的工具
- `tool_prediction` (bool)：默认 `False`。结构化推理模板要求模型列出它预期需要的工具。**需配合 `structured_reasoning=True` 才有效**

## 示例

```python
from amrita_core.config import AmritaConfig, BuiltinAgentConfig, ReactConfig

config = AmritaConfig(
    builtin=BuiltinAgentConfig(
        react_config=ReactConfig(
            structured_reasoning=True,
            reasoning_depth=4,
            tool_prediction=True,
            reasoning_aware_tools=True,
            enable_reflection=True,
            reflection_depth=2,
        )
    )
)
```

## 相关

- [BuiltinAgentConfig](BuiltinAgentConfig.md)——父对象
- [ReActAgentStrategy](ReActAgentStrategy.md)——被本配置作用的策略
