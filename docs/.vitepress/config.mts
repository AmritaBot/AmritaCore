import { defineConfig } from "vitepress";
import { withMermaid } from "vitepress-plugin-mermaid";

// https://vitepress.dev/reference/site-config
export default withMermaid({
  lastUpdated: true,
  ignoreDeadLinks: true,
  sitemap: {
    hostname: "https://core.amritabot.com",
  },
  locales: {
    root: {
      label: "English",
      lang: "en-US",
      title: "AmritaCore - Next-Gen AI Agent Framework",
      description:
        "AmritaCore is a lightweight, high-performance Python framework for building AI agents with streaming output, tool integration, MCP support, and event-driven architecture. Perfect for LLM-based applications.",
      head: [
        // Icon
        [
          "link",
          {
            rel: "icon",
            href: "/Amrita.png",
          },
        ],
        // SEO Meta Tags
        [
          "meta",
          {
            name: "keywords",
            content:
              "AI agent, Python framework, LLM, language model, streaming, MCP, tool calling, async, DeepSeek, OpenAI, Claude, artificial intelligence",
          },
        ],
        ["meta", { name: "author", content: "Project.Amrita" }],
        [
          "meta",
          {
            property: "og:title",
            content: "AmritaCore - Next-Generation AI Agent Framework",
          },
        ],
        [
          "meta",
          {
            property: "og:description",
            content:
              "Build powerful AI agents with streaming output, tool integration, and event-driven architecture using Python",
          },
        ],
        ["meta", { property: "og:type", content: "website" }],
        ["meta", { name: "twitter:card", content: "summary" }],
        [
          "meta",
          { name: "twitter:title", content: "AmritaCore - AI Agent Framework" },
        ],
        [
          "meta",
          {
            name: "twitter:description",
            content:
              "Lightweight Python framework for building AI agents with streaming, tools, and MCP support",
          },
        ],
      ],
      themeConfig: {
        // https://vitepress.dev/reference/default-theme-config
        siteTitle: "Amrita Core Docs",
        nav: [
          { text: "Home", link: "/" },
          { text: "Start", link: "/guide/introduction" },
        ],
        logo: "/Amrita.png",

        sidebar: [
          {
            text: "Introduction",
            collapsed: false,
            items: [
              { text: "Overview", link: "/guide/introduction/" },
              { text: "Key Features", link: "/guide/introduction/features" },
            ],
          },
          {
            text: "Getting Started",
            collapsed: false,
            items: [
              { text: "Index", link: "/guide/getting-started/" },
              {
                text: "Minimal Example",
                link: "/guide/getting-started/minimal-example",
              },
              {
                text: "Basic Example",
                link: "/guide/getting-started/basic-example",
              },
              {
                text: "Architecture Understanding",
                link: "/guide/getting-started/architecture",
              },
            ],
          },
          {
            text: "Core Concepts",
            collapsed: false,
            items: [
              { text: "Index", link: "/guide/concepts/" },
              { text: "Event System", link: "/guide/concepts/event" },
              { text: "Tool System", link: "/guide/concepts/tool" },
              { text: "Data Management", link: "/guide/concepts/management" },
              {
                text: "Agent Strategy",
                link: "/guide/concepts/agent-strategy",
              },
              {
                text: "Suspend Mechanism",
                link: "/guide/concepts/suspend",
              },
            ],
          },
          {
            text: "Implementation Guide",
            collapsed: false,
            items: [
              {
                text: "Function Implementation",
                link: "/guide/function-implementation",
              },
            ],
          },
          {
            text: "Extensions & Integration",
            collapsed: false,
            items: [
              {
                text: "Extensions & Integration",
                link: "/guide/extensions-integration",
              },
              {
                text: "Jinja2 Templates",
                link: "/guide/extensions-integration/jinja2-templates",
              },
              {
                text: "MCP Server Integration",
                link: "/guide/extensions-integration/mcp-server-integration",
              },
            ],
          },
          {
            text: "Security Mechanisms",
            collapsed: false,
            items: [
              {
                text: "Security Mechanisms",
                link: "/guide/security-mechanisms",
              },
            ],
          },
          {
            text: "API Reference",
            collapsed: true,
            items: [
              { text: "Index", link: "/guide/api-reference/" },
              {
                text: "AmritaConfig",
                link: "/guide/api-reference/classes/AmritaConfig",
              },
              {
                text: "AgentRuntime",
                link: "/guide/api-reference/classes/AgentRuntime",
              },
              {
                text: "AgentStrategy",
                link: "/guide/api-reference/classes/AgentStrategy",
              },
              {
                text: "AmritaAgentStrategy",
                link: "/guide/api-reference/classes/AmritaAgentStrategy",
              },
              {
                text: "BaseModel",
                link: "/guide/api-reference/classes/BaseModel",
              },
              {
                text: "BaseReActAgentStrategy",
                link: "/guide/api-reference/classes/BaseReActAgentStrategy",
              },
              {
                text: "ChatObject",
                link: "/guide/api-reference/classes/ChatObject",
              },
              {
                text: "ClientManager",
                link: "/guide/api-reference/classes/ClientManager",
              },
              {
                text: "Depends",
                link: "/guide/api-reference/classes/Depends",
              },
              {
                text: "DependsFactory",
                link: "/guide/api-reference/classes/DependsFactory",
              },
              {
                text: "FallbackContext",
                link: "/guide/api-reference/classes/FallbackContext",
              },
              {
                text: "Function",
                link: "/guide/api-reference/classes/Function",
              },
              {
                text: "FunctionDefinitionSchema",
                link: "/guide/api-reference/classes/FunctionDefinitionSchema",
              },
              {
                text: "HybridReActAgentStrategy",
                link: "/guide/api-reference/classes/HybridReActAgentStrategy",
              },
              {
                text: "MemoryModel",
                link: "/guide/api-reference/classes/MemoryModel",
              },
              {
                text: "Message",
                link: "/guide/api-reference/classes/Message",
              },
              {
                text: "ModelConfig",
                link: "/guide/api-reference/classes/ModelConfig",
              },
              {
                text: "ModelPreset",
                link: "/guide/api-reference/classes/ModelPreset",
              },
              {
                text: "ModelAdapter",
                link: "/guide/api-reference/classes/ModelAdapter",
              },
              {
                text: "MCPClient",
                link: "/guide/api-reference/classes/MCPClient",
              },
              {
                text: "MultiClientManager",
                link: "/guide/api-reference/classes/MultiClientManager",
              },
              {
                text: "NoActionAgentStrategy",
                link: "/guide/api-reference/classes/NoActionAgentStrategy",
              },
              {
                text: "PresetManager",
                link: "/guide/api-reference/classes/PresetManager",
              },
              {
                text: "ReActAgentStrategy",
                link: "/guide/api-reference/classes/ReActAgentStrategy",
              },
              {
                text: "StrategyContext",
                link: "/guide/api-reference/classes/StrategyContext",
              },
              {
                text: "SuspendEnum",
                link: "/guide/api-reference/classes/SuspendEnum",
              },
              {
                text: "SuspendObjectStream",
                link: "/guide/api-reference/classes/SuspendObjectStream",
              },
              {
                text: "EmbeddingChunk",
                link: "/guide/api-reference/classes/EmbeddingChunk",
              },
              {
                text: "TextContent",
                link: "/guide/api-reference/classes/TextContent",
              },
              {
                text: "ToolCall",
                link: "/guide/api-reference/classes/ToolCall",
              },
              {
                text: "ToolContext",
                link: "/guide/api-reference/classes/ToolContext",
              },
              {
                text: "ToolResult",
                link: "/guide/api-reference/classes/ToolResult",
              },
              {
                text: "ToolsManager",
                link: "/guide/api-reference/classes/ToolsManager",
              },
              {
                text: "UniResponse",
                link: "/guide/api-reference/classes/UniResponse",
              },
              {
                text: "UniResponseUsage",
                link: "/guide/api-reference/classes/UniResponseUsage",
              },
            ],
          },
          {
            text: "Builtin Functions",
            collapsed: false,
            items: [{ text: "Index", link: "/guide/builtins" }],
          },
          {
            text: "Appendix",
            collapsed: false,
            items: [{ text: "Appendix", link: "/guide/appendix" }],
          },
        ],
        footer: {
          message: `MIT License`,
          copyright: `© Amrita 2025-${new Date().getFullYear()}`,
        },
        socialLinks: [
          { icon: "github", link: "https://github.com/AmritaBot/AmritaCore" },
        ],
      },
    },
    zh: {
      label: "简体中文",
      lang: "zh-CN",
      title: "AmritaCore - 下一代 AI 智能体框架",
      description:
        "AmritaCore 是一个轻量级、高性能的 Python 框架，用于构建具有流式输出、工具集成、MCP 支持和事件驱动架构的 AI 智能体。适用于基于 LLM 的应用开发。",
      head: [
        [
          "link",
          {
            rel: "icon",
            href: "/Amrita.png",
          },
        ],
        // SEO Meta Tags
        [
          "meta",
          {
            name: "keywords",
            content:
              "AI 智能体，Python 框架，大语言模型，LLM,流式输出，MCP，工具调用，异步，DeepSeek，OpenAI，Claude，人工智能",
          },
        ],
        ["meta", { name: "author", content: "Project.Amrita" }],
        [
          "meta",
          {
            property: "og:title",
            content: "AmritaCore - 下一代 AI 智能体框架",
          },
        ],
        [
          "meta",
          {
            property: "og:description",
            content:
              "使用 Python 构建强大的 AI 智能体，支持流式输出、工具集成和事件驱动架构",
          },
        ],
        ["meta", { property: "og:type", content: "website" }],
        ["meta", { name: "twitter:card", content: "summary" }],
        [
          "meta",
          { name: "twitter:title", content: "AmritaCore - AI 智能体框架" },
        ],
        [
          "meta",
          {
            name: "twitter:description",
            content:
              "轻量级 Python 框架，支持流式输出、工具调用和 MCP 协议的 AI 智能体开发",
          },
        ],
      ],
      themeConfig: {
        // https://vitepress.dev/reference/default-theme-config
        siteTitle: "Amrita Core 文档",
        nav: [
          { text: "首页", link: "/zh/" },
          { text: "开始", link: "/zh/guide/introduction" },
        ],
        logo: "/Amrita.png",

        sidebar: [
          {
            text: "介绍",
            collapsed: false,
            items: [
              { text: "概述", link: "/zh/guide/introduction/" },
              {
                text: "主要特性",
                link: "/zh/guide/introduction/features",
              },
            ],
          },
          {
            text: "快速开始",
            collapsed: false,
            items: [
              { text: "索引", link: "/zh/guide/getting-started/" },
              {
                text: "最小示例",
                link: "/zh/guide/getting-started/minimal-example",
              },
              {
                text: "基础示例",
                link: "/zh/guide/getting-started/basic-example",
              },
              {
                text: "架构理解",
                link: "/zh/guide/getting-started/architecture",
              },
            ],
          },
          {
            text: "核心概念",
            collapsed: false,
            items: [
              { text: "索引", link: "/zh/guide/concepts/" },
              { text: "事件系统", link: "/zh/guide/concepts/event" },
              { text: "工具系统", link: "/zh/guide/concepts/tool" },
              { text: "数据管理", link: "/zh/guide/concepts/management" },
              { text: "Agent 策略", link: "/zh/guide/concepts/agent-strategy" },
              {
                text: "挂起机制",
                link: "/zh/guide/concepts/suspend",
              },
            ],
          },
          {
            text: "实现指南",
            collapsed: false,
            items: [
              {
                text: "函数实现",
                link: "/zh/guide/function-implementation",
              },
            ],
          },
          {
            text: "扩展与集成",
            collapsed: false,
            items: [
              {
                text: "扩展与集成",
                link: "/zh/guide/extensions-integration",
              },
              {
                text: "Jinja2 模板",
                link: "/zh/guide/extensions-integration/jinja2-templates",
              },
              {
                text: "MCP 服务器集成",
                link: "/zh/guide/extensions-integration/mcp-server-integration",
              },
            ],
          },
          {
            text: "安全机制",
            collapsed: false,
            items: [
              { text: "安全机制", link: "/zh/guide/security-mechanisms" },
            ],
          },
          {
            text: "API 参考",
            collapsed: true,
            items: [
              { text: "索引", link: "/zh/guide/api-reference/" },
              {
                text: "AmritaConfig",
                link: "/zh/guide/api-reference/classes/AmritaConfig",
              },
              {
                text: "AgentRuntime",
                link: "/zh/guide/api-reference/classes/AgentRuntime",
              },
              {
                text: "AgentStrategy",
                link: "/zh/guide/api-reference/classes/AgentStrategy",
              },
              {
                text: "AmritaAgentStrategy",
                link: "/zh/guide/api-reference/classes/AmritaAgentStrategy",
              },
              {
                text: "BaseModel",
                link: "/zh/guide/api-reference/classes/BaseModel",
              },
              {
                text: "BaseReActAgentStrategy",
                link: "/zh/guide/api-reference/classes/BaseReActAgentStrategy",
              },
              {
                text: "ChatObject",
                link: "/zh/guide/api-reference/classes/ChatObject",
              },
              {
                text: "ClientManager",
                link: "/zh/guide/api-reference/classes/ClientManager",
              },
              {
                text: "Depends",
                link: "/zh/guide/api-reference/classes/Depends",
              },
              {
                text: "DependsFactory",
                link: "/zh/guide/api-reference/classes/DependsFactory",
              },
              {
                text: "FallbackContext",
                link: "/zh/guide/api-reference/classes/FallbackContext",
              },
              {
                text: "Function",
                link: "/zh/guide/api-reference/classes/Function",
              },
              {
                text: "FunctionDefinitionSchema",
                link: "/zh/guide/api-reference/classes/FunctionDefinitionSchema",
              },
              {
                text: "HybridReActAgentStrategy",
                link: "/zh/guide/api-reference/classes/HybridReActAgentStrategy",
              },
              {
                text: "MemoryModel",
                link: "/zh/guide/api-reference/classes/MemoryModel",
              },
              {
                text: "Message",
                link: "/zh/guide/api-reference/classes/Message",
              },
              {
                text: "ModelConfig",
                link: "/zh/guide/api-reference/classes/ModelConfig",
              },
              {
                text: "ModelPreset",
                link: "/zh/guide/api-reference/classes/ModelPreset",
              },
              {
                text: "ModelAdapter",
                link: "/zh/guide/api-reference/classes/ModelAdapter",
              },
              {
                text: "MCPClient",
                link: "/zh/guide/api-reference/classes/MCPClient",
              },
              {
                text: "MultiClientManager",
                link: "/zh/guide/api-reference/classes/MultiClientManager",
              },
              {
                text: "NoActionAgentStrategy",
                link: "/zh/guide/api-reference/classes/NoActionAgentStrategy",
              },
              {
                text: "PresetManager",
                link: "/zh/guide/api-reference/classes/PresetManager",
              },
              {
                text: "ReActAgentStrategy",
                link: "/zh/guide/api-reference/classes/ReActAgentStrategy",
              },
              {
                text: "StrategyContext",
                link: "/zh/guide/api-reference/classes/StrategyContext",
              },
              {
                text: "SuspendEnum",
                link: "/zh/guide/api-reference/classes/SuspendEnum",
              },
              {
                text: "SuspendObjectStream",
                link: "/zh/guide/api-reference/classes/SuspendObjectStream",
              },
              {
                text: "EmbeddingChunk",
                link: "/zh/guide/api-reference/classes/EmbeddingChunk",
              },
              {
                text: "TextContent",
                link: "/zh/guide/api-reference/classes/TextContent",
              },
              {
                text: "ToolCall",
                link: "/zh/guide/api-reference/classes/ToolCall",
              },
              {
                text: "ToolContext",
                link: "/zh/guide/api-reference/classes/ToolContext",
              },
              {
                text: "ToolResult",
                link: "/zh/guide/api-reference/classes/ToolResult",
              },
              {
                text: "ToolsManager",
                link: "/zh/guide/api-reference/classes/ToolsManager",
              },
              {
                text: "UniResponse",
                link: "/zh/guide/api-reference/classes/UniResponse",
              },
              {
                text: "UniResponseUsage",
                link: "/zh/guide/api-reference/classes/UniResponseUsage",
              },
            ],
          },
          {
            text: "内置能力",
            collapsed: false,
            items: [{ text: "索引", link: "/zh/guide/builtins" }],
          },
          {
            text: "附录",
            collapsed: false,
            items: [{ text: "附录", link: "/zh/guide/appendix" }],
          },
        ],
        footer: {
          message: `MIT 许可证(一些内容可能没有完全翻译成中文，请以英文文档为准。)`,
          copyright: `© Amrita 2025-${new Date().getFullYear()}`,
        },
        socialLinks: [
          { icon: "github", link: "https://github.com/AmritaBot/AmritaCore" },
          { icon: "discord", link: "https://discord.gg/byAD3sbjjj" },
        ],
      },
    },
  },
  mermaidPlugin: {
    class: "mermaid my-class", // set additional css classes for parent container
  },
});
