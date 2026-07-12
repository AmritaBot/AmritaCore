---
layout: home
hero:
  name: "AmritaCore"
  text: "下一代 AI 智能体框架"
  tagline: "流式输出 · 工具调用 · MCP 集成 · 事件驱动 — 构建能思考、能行动的智能体"
  image:
    src: /Amrita.png
    alt: 项目Logo

  actions:
    - theme: brand
      text: 开始使用
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
    details: 端到端实时逐 token 流式输出，从 Jinja2 模板渲染到 LLM 响应投递，全链路原生 async/await。
  - icon: 🔧
    title: 丰富的工具生态
    details: 一等公民的工具调用支持，JSON Schema 验证、MCP 协议集成，装饰器一行注册——零样板代码。
  - icon: 🎯
    title: 可插拔 Agent 策略
    details: ReAct、Hybrid 及自定义策略自由切换。内建计数器守卫、失败自动回滚、挂起/恢复钩子，掌控每一步。
  - icon: 🎣
    title: 事件驱动管线钩子
    details: 拦截每个处理阶段——完成前、完成后、工具调用、LLM 回退。动态注入上下文、修改消息、记录日志。
---
