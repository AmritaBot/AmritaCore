# 异常排查

下面是你真正会遇到的失败模式。每条给出症状、根因与修复。

## 1. Agent 循环调用同一工具

**症状**：agent 反复用相同参数调用同一工具；token 快速消耗。

**根因**：工具结果没有改变任何东西，但模型一直在试——经典 ReAct 失败。

**修复**（AmritaCore 已内置）：

| 机制             | 配置 / 触发                             | 效果                                                                                               |
| ---------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **停滞检测**     | `builtin.loop_reasoning_trigger = N`    | 一个 Step 内 N 个相同工具签名后注入 give-up prompt 并结束 Step                                     |
| **执行前取消**   | 同一触发                                | 第 N 个相同调用在*运行前*被取消，返回 `"Cancelled: Reach the max limit of repeatly calling tool."` |
| **硬性调用上限** | `function_config.agent_tool_call_limit` | 循环到达该轮数后无论如何停止                                                                       |

**调参**：任务合法重复工具（如轮询）时调高 `loop_reasoning_trigger`；
仍循环则调低 `agent_tool_call_limit`。

## 2. DeepSeek（或 thinking 模式）HTTP 400：`reasoning_content` 必须回传

**症状**：HTTP 400 "The `reasoning_content` in the thinking mode must be
passed back"，非偶发——thinking 模式下首次工具轮次后必现。

**根因**：thinking 供应商要求 assistant 的 `reasoning_content` 在后续请求
原样回传。两个历史 bug 造成过此问题：思考过滤器原地修改消息对象、工具结果
追加时丢弃 `reasoning_content`。

**修复**：v0.13 均已修复——过滤器浅拷贝消息而非原地修改；每个 assistant
消息追加都带回 `response_msg.reasoning_content`。编写自定义策略时请遵守
两条规则：**绝不在原地剥离 reasoning；始终原样回传**。

## 3. `insufficient tool messages following tool_calls message`

**症状**：OpenAI 兼容 API 拒绝请求。

**根因**：每个带 `tool_calls` 的 assistant 消息必须紧跟匹配的
`ToolResult` 消息。

**修复**：内置策略为每个 tool_call 追加**一条 assistant 消息**及其
`ToolResult`——绝不把多个调用塞进一条 assistant 消息，除非全部配对。
自定义策略遵循同样的配对规则（见 [Agent 策略](../concepts/agent-strategy.md)）。

## 4. 空响应（启用 thinking 时）

**症状**：模型有时返回空 `content`；分解或摘要调用失败。

**根因**：部分供应商在思考时返回 `''`。

**修复**：内置——空响应降级为回退而非崩溃（分解 → 直接运行；摘要 →
`"Completed <phase>"`）。警告日志包含**原始请求 id**（DeepSeek 为
`x-ds-trace-id`，OpenAI 为 `x-request-id`），可在供应商日志中定位：
`Empty decomposition response (request_id=..., thinking_content=True)`。

## 5. 无明显循环却烧 token

**症状**：用量很高但 agent 没在循环。

**检查清单**：

- `function_config.agent_tool_call_limit` —— 每次运行的硬上限
- `llm.memory_abstract_threshold` —— 长会话启用摘要
- Step 间压缩 —— prompt tokens 超阈值时 step 循环压缩历史
  （`step` 元数据 `extra_type="compress"`）
- 工具签名 —— 观察 `stall` 元数据确认检测生效

## 6. Peer 消息未到达 Agent

**症状**：`send_to_producer(...)` 成功但 agent 从未看到文本。

**根因**：peer 消息只在 **Step 边界**（`intro_step`）被消费；Step 内排队；
运行结束后丢弃（通道关闭）。

**修复**：在运行开始前（或 Step 之间）推送保证送达；运行中推送则接受它
可能在下一个边界被拾取——见[流式](../tutorials/streaming.md)。

## 7. `Global AmritaConfig is not initialized`

**症状**：注册工具时启动即 `RuntimeError`。

**根因**：在 `minimal_init()`/`set_config()` 之前调用了 `get_config()`。

**修复**：创建 agent 或注册读取配置的工具（如 `enable_if` lambda）前先
`await minimal_init(config)`。

## 下一步

[进阶](../advanced/index.md)——内部机制：工作流引擎、挂起与 Step 循环。
