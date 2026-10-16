# 5. 记忆与会话

## 为什么需要

一次对话不止一个请求：agent 应该记得前面说过什么。AmritaCore 把两件事分开：

- **`session_id`** —— 一次对话的*标识符*。它是**唯一的**：它命名一次对话，
  本身并不"共享"任何东西。
- **数据存储** —— 对话历史实际存放在哪里。这是**数据后端**的职责，不是框架的。

本教程展示两者如何配合。

## 1. 唯一的会话 ID

每个 `ChatObject` 需要一个唯一的 `session_id`（或预构建的 `context`——两者互斥）：

```python
import uuid

chat = agent.get_chatobject(
    "My name is Alice.",
    session_id=str(uuid.uuid4()),  # 每个对话唯一
)
async with chat.begin():
    ...
```

这个 id 传给后端，后端把它当作历史数据的存储键。不同 id 的两次对话**永远
独立**。

## 2. 谁存数据？后端

AmritaCore 本身**不存储**对话历史。它把 `session_id` 交给数据后端
（`AbilityBackend` / `MemoryBackend`），由后端决定数据存放在哪里：

- **`LegacyBackend`**（默认）—— 记忆保存在**进程内**：某个 id 的历史只存活
  于进程生命周期，存在全局容器中。
- **你自己的后端** —— 实现后端接口，把历史存到数据库、Redis、文件……
  （见[数据层](../concepts/data.md)）。

所以两个 `ChatObject` 是否"看到同一段历史"，由**后端的存储**决定，而不是
复用同一个 id。如果你的后端在某个 id 下存了数据，第二次用该 id 的对话就会
加载它；如果没存，就不会。

## 3. 历史管理

长会话会撞上下文上限。选择最旧历史如何处理：

```python
from amrita_core import minimal_init
from amrita_core.config import AmritaConfig

config = AmritaConfig()
config.llm.context_strategy = "compact"  # "compact" | "slide" | "none"
config.llm.compaction_trigger_ratio = 0.9  # 窗口用到 90% 时动手
config.llm.slide_target_ratio = 0.7  # slide 裁剪到的位置
await minimal_init(config)
```

`"compact"` 把最旧的轮次折叠成 LLM 摘要，要点得以保留，代价是每次裁剪多一次
调用；`"slide"` 按加权 token 估算丢弃最旧的消息——不额外调用、尾部原样保留，
但丢掉的轮次彻底消失；`"none"` 让历史无限增长，等 provider 在超出窗口时直接
拒绝请求。

两种策略都在两条触发线中先到者触发：

- **token 触发**：provider 为上一次请求上报的 prompt 大小达到
  `compaction_trigger_ratio` × 预设的 `max_context`
- **消息条数兜底**：历史达到 `llm.memory_length_limit`（默认 200）

`"compact"` 下摘要存放在 `memory.abstract`，由模板渲染进系统指令，因此被折叠
的轮次完全离开消息列表。`"slide"` 下不渲染任何东西——存活下来的尾部原样发出去。
（内置 step 策略还会执行 Step 间历史管理——见[Step 循环](../advanced/step-loop.md)。）

## 4. 容易踩的地方

- **`slide_target_ratio` 必须严格低于 `compaction_trigger_ratio`。** 触发线决定
  何时裁剪，目标值决定裁到哪。如果目标值等于或高于触发线，裁完的历史又落回
  触发线上，于是每次请求都再 slide 一次，白白丢轮次。配置在加载时就会拒绝这
  一对数值——会话每轮都在缩水，就是要找的症状。
- **token 触发完全依赖 provider 的 usage 上报。** 它读的是 provider 为*上一次*
  请求返回的数字，网关什么都不报，这条线就一直哑着。此时消息条数兜底是唯一
  的网：只有当所有在用的 provider 都上报 usage，才把 `memory_length_limit`
  设为 `0`。
- **切点不能把 tool call 变成孤儿。** 历史是一串 `tool_calls` / `tool` 配对，
  按任意下标切开就会留下一个找不到对应调用的 tool 消息，provider 会回
  `insufficient tool messages following tool_calls message`。内置 slide 挑的是
  安全切点而不是原始下标，并且在一整段都是孤儿时退化为保留尾部。如果你自己裁
  历史（自定义后端、自定义策略），这份账得你自己算。
- **`enable_overflow_recovery` 是兜底而不是方案。** provider 因超出窗口拒绝请求
  时，AmritaCore 按 `context_strategy` 收缩历史并重试一次。`"none"` 下该项被
  忽略，因为它从不重写历史。

经验换算：一条消息约 300 tokens，64k 窗口约对应 200 条消息。

## 5. 刚才发生了什么

- `session_id` 是一次对话的**唯一标识符**——只负责命名
- **数据后端**决定历史存在哪里、能存活多久
- 压缩让长会话保持在上下文窗口内

## 下一步

教程路径已完成。推荐下一步：

- [核心概念](../concepts/index.md)——理解底层发生了什么
- [扩展与集成](../extensions-integration/index.md)——适配器、MCP
- [代理工程](../agent-engineering/index.md)——提示词调优与异常排查
