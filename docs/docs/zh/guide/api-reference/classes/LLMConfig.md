# LLMConfig

LLMConfig 类定义 LLM 调用和记忆管理的配置参数。

## 属性

- `require_tools` (bool)：默认 `False`。是否强制每次调用至少使用一个工具
- `max_tokens` (int)：默认 `1000`。单次响应中生成的最大 token 数（必须 `>= 1`）。同时作为 [`ModelPreset.max_output`](ModelPreset.md) 的兜底
- `session_tokens_windows` (int)：默认 `65536`（64k）。当前预设未声明 `max_context` 时使用的兜底注意力窗口（必须 `>= 1`）
- `llm_timeout` (int)：默认 `60`。API 请求超时时间（秒）（必须 `>= 1`）
- `auto_retry` (bool)：默认 `True`。请求失败时自动重试
- `max_retries` (int)：默认 `3`。最大重试次数（必须 `>= 0`；`0` 表示不重试）
- `max_fallbacks` (int)：默认 `5`。最大预设回退次数（必须 `>= 1`；`0` 会导致所有请求立即失败）
- `enable_compaction` (bool)：默认 `True`。是否将长历史折叠为摘要。摘要存放在 [`MemoryModel.abstract`](MemoryModel.md)，由 train 模板渲染进系统指令
- `compaction_trigger_ratio` (float)：默认 `0.9`。强制压缩历史时占注意力窗口的比例（必须在 `(0, 1]`）。保持小于 `1.0` 是为了吸收“上次实测 prompt 大小”与“下次请求实际大小”之间的滞后
- `memory_length_limit` (int)：默认 `200`。不看 token 计数、强制触发压缩的消息条数兜底（必须 `>= 0`；`0` 表示禁用兜底）
- `enable_overflow_recovery` (bool)：默认 `True`。当 provider 因超出上下文窗口而拒绝请求时，是否压缩并重试一次
- `enable_multi_modal` (bool)：默认 `True`。是否启用多模态支持

## 注意力窗口与压缩

注意力窗口来自模型本身，而不是一个全局数字。每个 [`ModelPreset`](ModelPreset.md) 都可以声明自己的 `max_context`（输入预算）与 `max_output`（响应预留）；`session_tokens_windows` 与 `max_tokens` 仅在预设未设置时作为兜底。因此模型的真实上限跟随模型本身。

压缩在两条触发线中先到者触发：

- **token 触发**：provider 为上一次请求上报的 prompt 大小达到 `compaction_trigger_ratio` × `max_context`。全程不涉及本地分词器——度量值就是 provider 自己的 usage 上报
- **消息条数兜底**：历史达到 `memory_length_limit` 条。该兜底存在的原因是 token 触发依赖 provider 上报 usage；从不上报的网关否则会让历史无界增长

常规 Agent 消息（含工具调用及其结果）大致折算 300 tokens，因此 64k 窗口约对应 200 条消息。只有当你使用的所有 provider 都会上报 usage 时，才将 `memory_length_limit` 设为 `0`。

## 描述

LLMConfig 类继承自 BaseModel，通过 `AmritaConfig.llm` 公开。它控制 token 限制、重试/回退行为、历史压缩与多模态支持。

## 示例

```python
from amrita_core.config import LLMConfig

llm_config = LLMConfig(
    enable_compaction=True,
    compaction_trigger_ratio=0.85,  # 窗口用到 85% 时折叠
    memory_length_limit=200,  # 消息条数兜底
    enable_overflow_recovery=True,  # provider 报溢出时压缩并重试
)
```
