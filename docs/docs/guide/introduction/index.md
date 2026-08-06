# Project Introduction

> **Where this fits**: you have built agents, extended them, tuned them, and
> gone deep into the internals. This page explains the _why_ behind the
> project — read it at any time, but it makes most sense at the end of the
> journey.

## What is AmritaCore?

AmritaCore is a **flexible progressive Agent framework built on
[AmritaSense](https://sense.amritabot.com)** — a lightweight, infrastructure-
focused agent runtime.

**AmritaCore = AmritaSense (workflow engine + events + streaming) + Agent layer
(strategy, sessions, tools, MCP, adapters).**

- **Interactive-first**: real-time, responsive agent applications via native
  async streaming
- **Lightweight**: minimal dependencies, maximum performance
- **Vendor-agnostic**: data types and conversation management are independent
  of providers
- **Extensible**: adapters, custom tools, MCP clients, custom tokenizers
- **Security-aware**: built-in cookie detection, injection-aware defaults

## What it is not

AmritaCore is **not** a replacement for LangChain or LlamaIndex-style
frameworks. It provides the essential building blocks _atop a proven workflow
engine_ — if you need batteries-included chains and integrations, those
frameworks serve a different purpose.

## Mission

Deliver a lightweight yet powerful foundation for agent development that
prioritizes simplicity, performance, and flexibility — with the design
philosophies documented in the [Appendix](../appendix.md).
