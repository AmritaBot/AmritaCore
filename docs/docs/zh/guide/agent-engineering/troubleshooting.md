# 异常排查与踩坑指南

下面是你真正会遇到的失败模式。每条给出症状、根因与修复——方案来自
AmritaCore 的真实执行机制，而非道听途说。

## 1. Agent 循环调用同一工具

**症状**：agent 反复用相同参数调用同一工具；token 快速消耗。

**根因**：工具结果没有改变任何东西，但模型一直在试——经典 ReAct 失败。

**修复**（AmritaCore 已内置）：

| 机制             | 配置 / 触发                             | 效果                                                                                               |
| ---------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **停滞检测**     | `builtin.loop_reasoning_trigger = N`    | N 个相同工具签名后注入 give-up prompt 并结束 Step                                                  |
| **执行前取消**   | 同一触发                                | 第 N 个相同调用在*运行前*被取消，返回 `"Cancelled: Reach the max limit of repeatly calling tool."` |
| **硬性调用上限** | `function_config.agent_tool_call_limit` | 循环到达该轮数后无论如何停止                                                                       |

检测位置很关键。停滞检测是**每次迭代钩子**（`after_iteration`，在每轮
`STEP_EXEC` 之后调用）——必须活在循环*内部*。旧设计只在 `leave_step`
检查，而它在循环退出后才执行：模型卡在调用同一个工具时永远到不了
`leave_step`，停滞永不触发、token 无限燃烧。step 循环的 `iter_cond` 还带
硬上限（`called_count > max_times`），内层停滞无法超出预算。
`leave_step` 保留停滞检查作为幂等兜底。

**调参**：任务合法重复工具（如轮询）时调高 `loop_reasoning_trigger`；
仍循环则调低 `agent_tool_call_limit`。

## 2. HTTP 400：`reasoning_content` 必须回传

**症状**：HTTP 400 "The `reasoning_content` in the thinking mode must be
passed back"，非偶发——assistant 一旦产出推理，后续每次请求必现。

**根因**：部分供应商要求 assistant 的 `reasoning_content` 在后续请求
原样回传。**是否适用由供应商决定，与适配器无关**：Anthropic 只要开启
扩展思考就必须回传；DeepSeek 即使在 OpenAI 兼容模式下也要求回传。
所以触发条件不是"thinking 模式"，而是供应商本身。两个历史 bug 造成过
此问题：思考过滤器**原地修改活动消息对象**、工具结果追加时丢弃
`reasoning_content`。

**修复**：v0.13 均已修复——过滤器（`thinking_config.content_mode`）
浅拷贝消息（`model_copy(deep=False)`）而非原地修改；每个 assistant 消息
追加都**原样带回** `response_msg` 的思考字段（`reasoning_content`、
`reasoning_signature` 及任何供应商 extra——`Message` 允许 extra，全量
传递，不硬编码）。编写自定义策略时请遵守
两条规则：**绝不在原地剥离 reasoning；始终原样回传**——对所有供应商
都安全，对上述供应商则是必须。

## 3. `insufficient tool messages following tool_calls message`

**症状**：OpenAI 兼容 API 拒绝请求。

**根因**：每个带 `tool_calls` 的 assistant 消息必须紧跟匹配的
`ToolResult` 消息。

**修复**：内置策略把**一次响应里的所有 tool_call 放进一条 assistant
消息**，后面紧跟**全部** `ToolResult`（按调用顺序，全部配对）。绝不把
同一响应拆成多条 assistant——思考正文（`reasoning_content`）只出现一次，
强拆会让它在多条消息里重复出现，产生未定义行为。
自定义策略遵循同样的配对规则（见 [Agent 策略](../concepts/agent-strategy.md)）。
任何拆散 tool-call/result 配对的上下文注入（如计划状态注记）都会破坏契约
——AmritaCore 只在 Step 边界注入，绝不插在配对中间。

## 4. 空响应（启用 thinking 时）

**症状**：模型有时返回空 `content`；分解或摘要调用失败。

**根因**：部分供应商在思考时返回 `''`。

**修复**：内置——空响应降级为回退而非崩溃（分解 → 直接运行；摘要 →
`"Completed <phase>"`）。警告日志包含**原始请求 id**，可在供应商日志中
定位：`Empty decomposition response (request_id=..., thinking_content=True)`。

> **请求 id 陷阱**：DeepSeek 把追踪 id 放在 `x-ds-trace-id`
> （偶尔是 `eo-log-uuid`），**不是** OpenAI 的 `x-request-id`。适配器按序
> 探测这三个头，最后回退内部 id。在 DeepSeek 调用里 grep `x-request-id`
> 会一无所获——请按警告里的 id 搜索。

## 5. 无明显循环却烧 token

**症状**：用量很高但 agent 没在循环。

**检查清单**：

- `function_config.agent_tool_call_limit` —— 每次运行的硬上限
- `llm.memory_abstract_threshold` —— 长会话启用摘要
- `function_config.agent_step_token_budget` —— 每 Step 的 prompt-token
  预算；耗尽时 `iter_cond` 停止该 Step（`TokenBudget.exhausted`）
- Step 间压缩 —— prompt tokens 超阈值时 step 循环压缩历史
  （`step` 元数据 `extra_type="compress"`）；折叠时 tool-call/result
  成对保留，被保留的上下文形态良好
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
`await minimal_init(config)`（或 `set_config`）。

## 8. `Undefined protocol adapter: <name>`

**症状**：创建 agent 或测试 preset 时抛 `ValueError`。

**根因**：`ModelPreset.protocol` 指向从未注册的适配器。框架只内置
`"openai"` / `"__main__"`（OpenAI 兼容）与 `"anthropic"` / `"claude"`——
见[模型适配器](../extensions-integration/adapters.md)。

**修复**：牢记两层模型——**适配器**决定协议，**供应商**只是
`base_url` + `model`。DeepSeek 与 Azure **不是**协议，而是通过默认协议
访问的 OpenAI 兼容端点。只有目标走 Anthropic 线上格式时才设
`protocol="anthropic"`；引用自定义协议前先注册自己的适配器（
`get_adapter_protocol()`）。`create_agent()` **没有** `protocol` 参数——
它总是构造默认协议的 preset。

## 9. `ModelPreset(model_config=...)` 静默丢弃字段

**症状**：流式关闭、思考配置被忽略——没有报错，只是行为不对。

**根因**：`ModelPreset` 没有 `model_config` 字段（`extra="allow"`），
`ModelPreset(model_config={...})` 把字典当作未知额外字段吞掉。你本想放进
`ModelConfig` 的内容从未生效。

**修复**：用 `create_agent(model_config={...})`，它会把字典正确映射到
`ModelConfig`。`ThinkingConfig` 同理——通过 preset 的 `thinking_config`
字段传入，或走 `create_agent` 的 kwargs。

## 10. 测试 / 异步陷阱

写测试或把 AmritaCore 嵌入 runner 时会踩到：

- **`asyncio.wait_for(coro, timeout=0)` 立即超时**——协程根本没机会运行。
  非阻塞探测流时用小正数超时（如 `0.001`）。
- **AnyIO 流绑定创建它的事件循环**。一次测试里两次独立的
  `asyncio.run()` 会跨循环共享流并挂死。push + drain 必须放在同一个
  `asyncio.run()` 内。
- **`MagicMock` 流在 `__anext__` 上挂死**。流消费者要用
  `isinstance(stream, SuspendObjectStream)` 门卫；mock 在
  `get_producer_input_generator()` 上"成功"返回后，迭代会永远挂住。
- **`TypedDict` 元数据不能用 `isinstance` 检查**。`isinstance(m,
AgentStepXxxMetadata)` 抛 `TypeError`——用
  `m.get("type") == "step" and m.get("extra_type") == ...` 区分。
- **`patch.object(strategy, method, fake_fn)` 不会绑定 `self`**。用
  `new=AsyncMock()`（或绑定方法），被 patch 的可调用才能收到实例。

## 11. 计划修订（`update_step`）似乎无效

**症状**：模型从不调用 `update_step`；计划从不改变。

**根因**：三件事必须对齐，每一件历史上都出过问题：

1. **工具必须可见**。`UPDATE_STEP_TOOL` 只在 step 循环激活时暴露
   （`intro_step` 上的 `_ensure_step_tools`）。没有 step 循环工作流，
   模型根本看不到 `update_step`。
2. **计划必须在上下文中**。`_inject_plan_status()` 在 Step intro 时写入
   `[Plan status]` 快照——但只在快照变化时，且只在 Step 边界（绝不拆散
   tool-call/result 配对）。
3. **提示词引导是概率性的**。用散文告诉模型"调用 `update_step`"有时
   有效。可靠路径是**框架级确定性注入**：工具结果以 `ERROR` 开头时，
   `_maybe_inject_tool_failure_hint()` 追加一条 user 消息——首次失败
   "最多重试一次，然后调用 `update_step`（remove_step/replan）"，同 Step
   再次失败 "不要再重试，立即调用 update_step"（
   `AgentRunState.tool_error_hints` 按 Step 计数）。

**修复**：使用 step 循环工作流、保持计划可见，并依赖 `ERROR` 前缀约定
表示硬失败——框架会把失败工具确定性地变成明确的修订指令。

## 下一步

[进阶](../advanced/index.md)——内部机制：工作流引擎、挂起与 Step 循环。
