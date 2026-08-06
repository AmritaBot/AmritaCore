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
      link: /guide/getting-started
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
    title: Step-Driven Agent Strategies
    details: The built-in ReAct strategy runs as a native instruction-driven Step loop with DAG planning, stall detection and lifecycle events for full control.
  - icon: 🎣
    title: Event-Driven Pipeline Hooks
    details: Intercept every stage — step boundaries, tool calls, completions, and LLM fallback. Modify messages, inject context, or log responses on the fly.
---

## What is AmritaCore?

**AmritaCore is a lightweight Agent runtime built on [AmritaSense](https://sense.amritabot.com).**

```
AmritaCore = AmritaSense (workflow engine + events + streaming) + Agent layer (strategy, sessions, tools, MCP, adapters)
```

AmritaSense provides the **execution substrate** — a native-instruction workflow VM, a bidirectional
`SuspendObjectStream`, and a matcher-based event system. AmritaCore builds the **agent layer** on top:
conversation objects, tool calling, MCP clients, model adapters, and a built-in step-driven ReAct strategy.

> **Learning path**: The documentation follows the natural journey of building agents —
> run it first, extend it, tune it, then understand the internals.
> AmritaSense-specific topics are only _recapped inline_ where needed and linked to
> [sense.amritabot.com](https://sense.amritabot.com) — they are not duplicated here.

## Reading Path

| Stage               | Section                                                           | What you will get                                        |
| ------------------- | ----------------------------------------------------------------- | -------------------------------------------------------- |
| ① Run it            | [Getting Started](/guide/getting-started)                         | Environment, minimal example, first agent                |
| ② Use it            | [Tutorials](/guide/tutorials)                                     | Tools, streaming, hooks, memory — step by step           |
| ③ Understand it     | [Concepts](/guide/concepts)                                       | How ChatObject, strategies, events and data fit together |
| ④ Extend it         | [Extensions & Integration](/guide/extensions-integration)         | Adapters, custom tools, MCP, custom tokenizers           |
| ⑤ Tune it           | [Agent Engineering](/guide/agent-engineering)                     | Prompt engineering, Jinja2 templates, troubleshooting    |
| ⑥ Go deeper         | [Advanced](/guide/advanced)                                       | The workflow engine, suspend/resume, step-loop internals |
| ⑦ Design philosophy | [Introduction](/guide/introduction) + [Appendix](/guide/appendix) | Why AmritaCore is designed the way it is                 |

> **Shortcuts**: Prefer reference over prose? Jump straight to the [API Reference](/guide/api-reference),
> the [Built-in Capabilities](/guide/builtins), or the [Security Mechanisms](/guide/security-mechanisms).
