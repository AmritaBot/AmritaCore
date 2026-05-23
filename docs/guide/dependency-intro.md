# AmritaSense 依赖

> AmritaCore v0.9.0rc1 起，核心基础设施已抽取至 `amrita-sense` 包。

## 概述

`amrita-sense`（版本 >=0.2.1）是 AmritaCore 的**基础运行时**，提供工作流引擎、事件系统和流式处理能力。AmritaCore 在此之上构建 Agent 层（策略、会话、工具、MCP、适配器）。

**AmritaCore = AmritaSense + Agent 层**

完整文档：[**https://sense.amritabot.com**](https://sense.amritabot.com)

## 已迁移模块速查

| AmritaCore 旧路径                                                 | AmritaSense 新路径            | AmritaSense 文档                                                                           |
| ----------------------------------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------ |
| `amrita_core.streaming`                                           | `amrita_sense.streaming`      | [SuspendObjectStream API](https://sense.amritabot.com/reference/api/suspend-object-stream) |
| `amrita_core.logging`                                             | `amrita_sense.logging`        | 内置，无需单独文档                                                                         |
| `amrita_core.hook.event`                                          | `amrita_sense.hook.event`     | [事件系统](https://sense.amritabot.com/guide/advanced/event_system)                        |
| `amrita_core.hook.matcher`                                        | `amrita_sense.hook.matcher`   | [事件系统](https://sense.amritabot.com/guide/advanced/event_system)                        |
| `amrita_core.hook.exception`                                      | `amrita_sense.hook.exception` | [控制流](https://sense.amritabot.com/guide/concepts/flow_control)                          |
| 工作流引擎 (`Node`, `NodeComposeRendered`, `WorkflowInterpreter`) | `amrita_sense` 顶层           | [组合与执行](https://sense.amritabot.com/guide/concepts/compose_and_exec)                  |
| `ALIAS`, `ARCHIVED_NODES`                                         | `amrita_sense` 顶层           | [控制流](https://sense.amritabot.com/guide/concepts/flow_control)                          |
| 依赖注入 (`Depends`)                                              | `amrita_sense.runtime.deps`   | [依赖注入](https://sense.amritabot.com/guide/advanced/dependency_injection)                |

## 安装

```bash
pip install amrita_core
# amrita-sense 自动安装，无需手动操作
```

## 迁移指南

| 旧导入 (amrita_core)               | 新导入 (amrita-sense)               |
| ---------------------------------- | ----------------------------------- |
| `amrita_core.logging`              | `amrita_sense.logging`              |
| `amrita_core.streaming`            | `amrita_sense.streaming`            |
| `amrita_core.hook.matcher`         | `amrita_sense.hook.matcher`         |
| `amrita_core.hook.event.BaseEvent` | `amrita_sense.hook.event.BaseEvent` |
| `amrita_core.hook.exception`       | `amrita_sense.hook.exception`       |

旧导入路径仍可用但已弃用，会触发 `DeprecationWarning`。

## 版本要求

- **amrita-sense**: `>=0.2.1`
- **Python**: `>=3.10,<3.15`
