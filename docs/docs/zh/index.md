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
      link: /zh/guide/introduction
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
    title: 可插拔 Agent 策略
    details: 在 ReAct、Hybrid 和自定义策略间自由切换。内置计数器防护、失败回滚、挂起/恢复钩子，提供完全控制。
  - icon: 🎣
    title: 事件驱动管线钩子
    details: 拦截每个阶段——预完成、后完成、工具调用、LLM 回退。动态修改消息、注入上下文或记录响应。
---
