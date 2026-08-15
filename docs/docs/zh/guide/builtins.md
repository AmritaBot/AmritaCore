# 内置能力

## 内置工具

| 工具                                | 用途                                                                 |
| ----------------------------------- | -------------------------------------------------------------------- |
| `STOP_TOOL`（`agent_stop`）         | 结束工具循环；agent 直接作答                                         |
| `REASONING_TOOL`（`reasoning`）     | 显式推理步骤（非原生 thinking 模式）                                 |
| `UPDATE_STEP_TOOL`（`update_step`） | 修订任务计划：`replan` / `mark_done` / `add_step` / `remove_step`    |
| `PROCESS_MESSAGE`                   | 向用户报告 agent 进度（`function_config.agent_middle_message` 启用） |

内置工具绕过 `agent.tool_call` / `agent.tool_return` 生命周期事件，且被排除在
停滞签名取消之外。

## 内置元数据类型

流元数据（`MessageWithMetadata.metadata`）使用 `type` + `extra_type`：

| `type`                               | `extra_type`                                           | 含义                                                       |
| ------------------------------------ | ------------------------------------------------------ | ---------------------------------------------------------- |
| `function_call`                      | —                                                      | 工具开始/结束（`is_done`）                                 |
| `reasoning_chunk`                    | `cot_chunk`                                            | thinking 模式推理流式                                      |
| `reasoning` / `structured_reasoning` | —                                                      | 推理摘要                                                   |
| `reflection`                         | —                                                      | 停止后反思结果                                             |
| `error`                              | `loop_reasoning`                                       | 循环检测错误通知                                           |
| `step`                               | `decompose` / `intro` / `leave` / `stall` / `compress` | Step 循环生命周期（见 [Step 循环](advanced/step-loop.md)） |

## 内置适配器

见[模型适配器](extensions-integration/adapters.md)——OpenAI 兼容适配器
（通过 `base_url`/`model` 服务 OpenAI、DeepSeek、Azure 及任意 OpenAI 兼容
端点）与 Anthropic 适配器（`protocol="anthropic"`）。

## 内置策略

| 策略                       | 类别          | 备注                                                                                                         |
| -------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------ |
| `ReActAgentStrategy`       | `agent-mixed` | **默认策略类**；step 循环工作流激活后以节点驱动 Step 循环运行（见 [Agent 策略](concepts/agent-strategy.md)） |
| `HybridReActAgentStrategy` | `agent-mixed` | MoE XML 风格结果；**已弃用，v0.14.0 移除**                                                                   |
| `NoActionAgentStrategy`    | `workflow`    | 跳过工具调用                                                                                                 |

## 内置事件钩子

### Cookie 安全钩子

`config.cookie.enable_cookie = True` 时，响应会被扫描配置的 cookie 值；命中即
终止会话并返回通用错误防止数据泄露（见[安全](security-mechanisms.md)）。

### 后处理钩子

`strategy.on_post_process()` 在成功执行后对所有策略类别运行——最终指令、
摘要或清理。

## 内置工作流

`amrita_core.builtins.workflows` 中的预组合管线（见[工作流引擎](advanced/workflow-engine.md)）：

| 工作流                                                       | 管线                                         |
| ------------------------------------------------------------ | -------------------------------------------- |
| `SIMPLE_CHAT`                                                | 纯对话，无 agent（默认）                     |
| `REACT_BLOCK` / `SIMPLE_REACT` / `REACT_ONLY`                | 传统 ReAct 循环                              |
| `STEP_REACT_BLOCK` / `SIMPLE_STEP_REACT` / `STEP_REACT_ONLY` | Step 驱动 ReAct（显式启用）                  |
| `CHATOBJECT_STEP_REACT`                                      | 内部归档 step 循环（ChatObject runner 使用） |

> `workflow=None`（`ChatObject` 默认）解析为**简单对话**管线。Step 驱动系列
> 只在显式传入时运行——例如 `get_chatobject(..., workflow=SIMPLE_STEP_REACT)`
> 或 `workflow=_step_workflow_rendered`（见 [Step 循环](advanced/step-loop.md)）。
> `CHATOBJECT_STEP_REACT` 通常由框架替你选择——只在自行组合自定义管线需要
> 归档块变体时才手动传入。
