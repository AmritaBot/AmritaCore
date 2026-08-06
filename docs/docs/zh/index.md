---
layout: home
hero:
  name: "AmritaCore"
  text: "下一代 AI 智能体框架"
  tagline: "流式输出 · 工具调用 · MCP 集成 · 事件驱动 — 构建会思考、能行动的智能体"
  image:
    src: /Amrita.png
    alt: 项目 Logo

  actions:
    - theme: brand
      text: 快速开始
      link: /zh/guide/getting-started
    - theme: alt
      text: GitHub
      link: https://github.com/AmritaBot/AmritaCore
    - theme: alt
      text: 由 AmritaSense 驱动 ↗
      link: https://sense.amritabot.com

features:
  - icon: ⚡
    title: 流式输出 & 全异步
    details: 实时逐 token 流式输出，整个管线（从模板渲染到 LLM 响应交付）原生 async/await。
  - icon: 🔧
    title: 丰富的工具生态
    details: 一流的工具调用支持，含 JSON Schema 校验、MCP 协议支持、简洁的装饰器 API 定义自定义工具——无需样板代码。
  - icon: 🎯
    title: Step 驱动的 Agent 策略
    details: 内置 ReAct 策略以原生指令驱动的 Step 循环运行，支持 DAG 规划、停滞检测与生命周期事件，完全可控。
  - icon: 🎣
    title: 事件驱动管线钩子
    details: 拦截每个阶段——Step 边界、工具调用、完成、LLM 回退。动态修改消息、注入上下文或记录响应。
---

## 什么是 AmritaCore？

**AmritaCore 是构建于 [AmritaSense](https://sense.amritabot.com) 之上的轻量级 Agent 运行时。**

```
AmritaCore = AmritaSense（工作流引擎 + 事件 + 流） + Agent 层（策略、会话、工具、MCP、适配器）
```

AmritaSense 提供**执行基座**——原生指令工作流虚拟机、双向 `SuspendObjectStream`、
基于 matcher 的事件系统。AmritaCore 在其上构建 **Agent 层**：对话对象、工具调用、
MCP 客户端、模型适配器，以及内置的 Step 驱动 ReAct 策略。

> **学习路径**：本手册遵循构建 agent 的自然旅程——先跑起来、再扩展、再调优、
> 最后理解内部设计。AmritaSense 专属主题只在需要处**内联回顾**并链接到
> [sense.amritabot.com](https://sense.amritabot.com)——不做重复叙述。

## 阅读路径

| 阶段       | 版块                                                            | 你将获得                                  |
| ---------- | --------------------------------------------------------------- | ----------------------------------------- |
| ① 跑起来   | [快速开始](/zh/guide/getting-started)                           | 环境、最小示例、第一个 agent              |
| ② 用起来   | [教程](/zh/guide/tutorials)                                     | 工具、流式、钩子、记忆——循序渐进          |
| ③ 理解底层 | [核心概念](/zh/guide/concepts)                                  | ChatObject、策略、事件与数据如何协作      |
| ④ 扩展     | [扩展与集成](/zh/guide/extensions-integration)                  | 适配器、自定义工具、MCP、自定义 Tokenizer |
| ⑤ 调优     | [代理工程](/zh/guide/agent-engineering)                         | 提示词工程、Jinja2 模板、异常排查         |
| ⑥ 深入内核 | [进阶](/zh/guide/advanced)                                      | 工作流引擎、挂起/恢复、Step 循环内部      |
| ⑦ 设计哲学 | [项目介绍](/zh/guide/introduction) + [附录](/zh/guide/appendix) | AmritaCore 为何这样设计                   |

> **捷径**：偏好查阅而非通读？直接跳到 [API 参考](/zh/guide/api-reference)、
> [内置能力](/zh/guide/builtins) 或 [安全机制](/zh/guide/security-mechanisms)。
