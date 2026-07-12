---
layout: home
hero:
  name: "AmritaCore"
  text: "Next-Generation AI Agent Framework"
  tagline: "Streaming output · Tool calling · MCP integration · Event-driven — Build agents that think and act"
  image:
    src: /Amrita.png
    alt: Project Logo

  actions:
    - theme: brand
      text: Get Started
      link: /guide/introduction
    - theme: alt
      text: GitHub
      link: https://github.com/AmritaBot/AmritaCore
    - theme: alt
      text: Powered by AmritaSense ↗
      link: https://sense.amritabot.com

features:
  - icon: ⚡
    title: Streaming & Fully Async
    details: Real-time token-by-token streaming with native async/await throughout the entire pipeline — from template rendering to LLM response delivery.
  - icon: 🔧
    title: Rich Tool Ecosystem
    details: First-class tool calling with JSON Schema validation, MCP protocol support, and a simple decorator API for custom tools — no boilerplate required.
  - icon: 🎯
    title: Pluggable Agent Strategies
    details: Swap between ReAct, Hybrid, and custom strategies. Built-in counter guard, rollback on failure, and suspend/resume hooks for full control.
  - icon: 🎣
    title: Event-Driven Pipeline Hooks
    details: Intercept every stage — pre-completion, post-completion, tool calls, and LLM fallback. Modify messages, inject context, or log responses on the fly.
---
