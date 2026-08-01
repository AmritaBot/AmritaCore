# Project Introduction

## Project Overview

### What is AmritaCore?

AmritaCore is a **flexible progressive Agent framework built on [AmritaSense](https://sense.amritabot.com)**. It leverages the AmritaSense async workflow engine to deliver composable, high-performance agent execution with minimal overhead.

**AmritaCore = AmritaSense (workflow engine + events + streaming) + Agent layer (strategy, sessions, tools, MCP, adapters).**

**AmritaCore is designed to be interactive-first**, enabling real-time, responsive agent applications through AmritaSense's native async streaming architecture.

Think of AmritaCore as providing the essential "operating system" capabilities for AI agents — offering core primitives and abstractions that enable robust, production-ready agent applications without the overhead of heavyweight frameworks.

**AmritaCore is not a replacement for existing frameworks** like LangChain or LlamaIndex. Instead, it is a **lightweight, infrastructure-focused agent framework** that provides essential building blocks atop a proven workflow engine.

### Project Background and Mission

The mission of AmritaCore is to provide a lightweight yet powerful foundation for agent development that prioritizes simplicity, performance, and flexibility. As AI applications demand real-time responsiveness and efficient resource utilization, there's a need for frameworks that:

- Deliver **stream-based design** for real-time responses
- Ensure **security** with built-in cookie security detection
- Maintain **vendor agnostic** approach for high portability
- Enable **extensibility** through integrated MCP client support
- Provide **minimal dependencies** and **maximum performance**

AmritaCore addresses these requirements with a focused architecture that emphasizes core capabilities while avoiding unnecessary complexity.

### Core Value Propositions

- **Built on AmritaSense**: Leverages a battle-tested async workflow engine with composable nodes, dependency injection, and native control flow (IF/WHILE/JUMP/TRY)
- **Stream-based Design**: All message outputs are designed as asynchronous streams for real-time responses
- **Lightweight Architecture**: Minimal dependencies and maximum performance for resource-constrained environments
- **Interactive-First**: Native async streaming architecture optimized for real-time, responsive applications
- **Infrastructure-Level**: Provides essential "operating system" capabilities for AI agents
- **Security**: Built-in cookie security detection to ensure session safety
- **Vendor Agnostic**: Data types and conversation management independent of specific providers
- **Extensibility**: Integrated MCP client in extension mechanisms for enhanced system scalability
