# LLMConfig

LLMConfig 类定义 LLM 调用和记忆管理的配置参数。

## 属性

- `require_tools` (bool)：默认 `False`。是否强制每次调用至少使用一个工具
- `max_tokens` (int)：默认 `10000`。响应输出预算的最后兜底（必须 `>= 1`）。真正发给 provider 的数字通常来自 [`ModelPreset.max_output`](ModelPreset.md)（默认 `28000`）；只有当预设显式设置 `max_output=None` 时才会用到本项
- `compaction_max_tokens` (int)：默认 `2048`。历史压缩摘要调用的输出上限（必须 `>= 0`；`0` 表示摘要沿用预设自身的值）。推理模型在产出任何内容之前会先花掉输出预算思考，因此继承较小 `max_output` 的摘要会返回空内容，导致折叠静默不生效
- `session_tokens_windows` (int)：默认 `65536`（64k）。当前预设未声明 `max_context` 时使用的兜底注意力窗口（必须 `>= 1`）
- `llm_timeout` (int)：默认 `60`。API 请求超时时间（秒）（必须 `>= 1`）
- `max_retries` (int)：默认 `3`。最大重试次数（必须 `>= 0`；`0` 表示不重试）
- `max_fallbacks` (int)：默认 `5`。最大预设回退次数（必须 `>= 1`；`0` 会导致所有请求立即失败）
- `context_strategy` (Literal)：默认 `"compact"`。历史超出预算后如何处理——`"compact"`、`"slide"` 或 `"none"`。见[历史策略](#历史策略)
- `compaction_trigger_ratio` (float)：默认 `0.9`。强制管理历史时占注意力窗口的比例（必须在 `(0, 1]`）。保持小于 `1.0` 是为了吸收“上次实测 prompt 大小”与“下次请求实际大小”之间的滞后
- `slide_target_ratio` (float)：默认 `0.7`。`"slide"` 将历史裁剪到的注意力窗口比例（必须在 `(0, 1]`；大于等于 `compaction_trigger_ratio` 会被校验器拒绝，因为裁剪后落回触发线会导致每次请求都重新裁剪）
- `memory_length_limit` (int)：默认 `200`。不看 token 计数、强制触发历史管理的消息条数兜底（必须 `>= 0`；`0` 表示禁用兜底）
- `enable_overflow_recovery` (bool)：默认 `True`。当 provider 因超出上下文窗口而拒绝请求时，是否缩小历史并重试一次。缩小方式跟随 `context_strategy`，与回合间的路径一致（`"none"` 下忽略）
- `enable_multi_modal` (bool)：默认 `True`。是否启用多模态支持

## 注意力窗口与历史策略

注意力窗口来自模型本身，而不是一个全局数字。每个 [`ModelPreset`](ModelPreset.md) 都可以声明自己的 `max_context`（输入预算）与 `max_output`（响应预留）；`session_tokens_windows` 与 `max_tokens` 仅在预设未设置时作为兜底。因此模型的真实上限跟随模型本身。

历史管理在两条触发线中先到者触发：

- **token 触发**：provider 为上一次请求上报的 prompt 大小达到 `compaction_trigger_ratio` × `max_context`。全程不涉及本地分词器——度量值就是 provider 自己的 usage 上报
- **消息条数兜底**：历史达到 `memory_length_limit` 条。该兜底存在的原因是 token 触发依赖 provider 上报 usage；从不上报的网关否则会让历史无界增长。`"slide"` 下没有可用测量值时，这个条数上限同时就是裁剪目标

常规 Agent 消息（含工具调用及其结果）大致折算 300 tokens，因此 64k 窗口约对应 200 条消息。只有当你使用的所有 provider 都会上报 usage 时，才将 `memory_length_limit` 设为 `0`。

### 历史策略

触发后做什么由 `context_strategy` 决定：

| 取值        | 行为                                                                                                                                            |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `"compact"` | 把最旧的一段折叠成 LLM 摘要，存放在 [`MemoryModel.abstract`](MemoryModel.md)，由 train 模板渲染回系统指令。代价是多一次模型调用，但要点得以保留 |
| `"slide"`   | 直接丢弃最旧的消息，裁剪到 `slide_target_ratio` × `max_context`；没有可用测量值时则裁到 `memory_length_limit` 条。不额外调用模型，尾部保持原文，但被丢弃的内容彻底消失                           |
| `"none"`    | 完全不碰历史，任其无界增长，超出窗口时由 provider 拒绝请求                                                                                      |

`"slide"` 按每条消息在已上报 prompt 大小中的占比做加权估算，因此同样不需要分词器：权重经过归一化，求和会回到实测值。它不会在轮次中间切断，也不会留下“声明它的调用已被删除”的游离工具结果，因此裁剪后的负载依然能通过网关校验。

当早期轮次可以丢弃（长时间的工具调用会话）且每次裁剪都多花一次摘要调用太贵时，用 `"slide"`；当早期轮次仍携带后续轮次依赖的决策时，用 `"compact"`。

## 描述

LLMConfig 类继承自 BaseModel，通过 `AmritaConfig.llm` 公开。它控制 token 限制、重试/回退行为、历史管理与多模态支持。

## 示例

```python
from amrita_core.config import LLMConfig

llm_config = LLMConfig(
    context_strategy="compact",  # "compact" | "slide" | "none"
    compaction_trigger_ratio=0.85,  # 窗口用到 85% 时动手
    slide_target_ratio=0.7,  # "slide" 下裁剪回 70%
    memory_length_limit=200,  # 消息条数兜底
    enable_overflow_recovery=True,  # provider 报溢出时缩小历史并重试
)
```
