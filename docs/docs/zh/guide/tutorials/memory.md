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

## 3. 记忆摘要

长会话会撞上下文上限。开启自动压缩：

```python
from amrita_core import minimal_init
from amrita_core.config import AmritaConfig

config = AmritaConfig()
config.llm.enable_compaction = True
config.llm.compaction_trigger_ratio = 0.9  # 窗口用到 90% 时折叠
await minimal_init(config)
```

压缩在两条触发线中先到者触发：

- **token 触发**：provider 为上一次请求上报的 prompt 大小达到
  `compaction_trigger_ratio` × 预设的 `max_context`
- **消息条数兜底**：历史达到 `llm.memory_length_limit`（默认 200）

摘要存放在 `memory.abstract`，由模板渲染进系统指令，因此被折叠的轮次完全
离开消息列表。（内置 step 策略还会执行 Step 间压缩——见
[Step 循环](../advanced/step-loop.md)。）

经验换算：一条消息约 300 tokens，64k 窗口约对应 200 条消息。只有当所有
provider 都会上报 usage 时，才将 `memory_length_limit` 设为 `0`。

## 4. 刚才发生了什么

- `session_id` 是一次对话的**唯一标识符**——只负责命名
- **数据后端**决定历史存在哪里、能存活多久
- 压缩让长会话保持在上下文窗口内

## 下一步

教程路径已完成。推荐下一步：

- [核心概念](../concepts/index.md)——理解底层发生了什么
- [扩展与集成](../extensions-integration/index.md)——适配器、MCP
- [代理工程](../agent-engineering/index.md)——提示词调优与异常排查
