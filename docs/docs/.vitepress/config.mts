import { defineConfig } from "vitepress";
import { withMermaid } from "vitepress-plugin-mermaid";

// https://vitepress.dev/reference/site-config
export default withMermaid({
  lastUpdated: true,
  ignoreDeadLinks: true,
  vite: {
    build: {
      rollupOptions: {
        onLog(level, log, handler) {
          if (log.message?.includes("points to missing source files")) return;
          handler(level, log);
        },
      },
    },
    optimizeDeps: {
      exclude: [
        "@nolebase/vitepress-plugin-enhanced-readabilities/client",
        "vitepress",
        "@nolebase/ui",
      ],
    },
    ssr: {
      noExternal: [
        "@nolebase/vitepress-plugin-enhanced-readabilities",
        "@nolebase/ui",
      ],
    },
  },
  sitemap: {
    hostname: "https://core.amritabot.com",
  },
  themeConfig: {
    search: {
      provider: "local",
    },
  },
  head: [
    ["link", { rel: "icon", href: "/Amrita.png" }],
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
  locales: {
    root: {
      label: "English",
      lang: "en-US",
      title: "AmritaCore - Next-Gen AI Agent Framework",
      description:
        "AmritaCore is a lightweight, high-performance Python framework for building AI agents with streaming output, tool integration, MCP support, and event-driven architecture. Perfect for LLM-based applications.",
      themeConfig: {
        siteTitle: "Amrita Core Docs",
        nav: [
          { text: "Home", link: "/" },
          { text: "Start", link: "/guide/introduction" },
        ],
        logo: "/Amrita.png",
        sidebar: [
          {
            text: "Getting Started",
            collapsed: false,
            items: [
              { text: "Index", link: "/guide/getting-started/" },
              {
                text: "Basic Example",
                link: "/guide/getting-started/basic-example",
              },
              {
                text: "Minimal Example",
                link: "/guide/getting-started/minimal-example",
              },
            ],
          },
          {
            text: "Tutorials",
            collapsed: false,
            items: [
              { text: "Index", link: "/guide/tutorials/" },
              {
                text: "Create Your First Agent",
                link: "/guide/tutorials/chat-object",
              },
              {
                text: "Events and Hooks",
                link: "/guide/tutorials/event-hooks",
              },
              {
                text: "Memory and Sessions",
                link: "/guide/tutorials/memory",
              },
              {
                text: "Streaming and Callbacks",
                link: "/guide/tutorials/streaming",
              },
              {
                text: "Add Tools to Your Agent",
                link: "/guide/tutorials/tools",
              },
            ],
          },
          {
            text: "Core Concepts",
            collapsed: false,
            items: [
              { text: "Index", link: "/guide/concepts/" },
              {
                text: "Agent Strategy",
                link: "/guide/concepts/agent-strategy",
              },
              {
                text: "ChatObject — Lifecycle Manager",
                link: "/guide/concepts/chat-object",
              },
              {
                text: "Configuration",
                link: "/guide/concepts/configuration",
              },
              { text: "Data Management", link: "/guide/concepts/data" },
              { text: "Data Backend", link: "/guide/concepts/data-backend" },
              { text: "Memory Model", link: "/guide/concepts/data-memory" },
              { text: "Event System", link: "/guide/concepts/event" },
              { text: "Tool System", link: "/guide/concepts/tool" },
            ],
          },
          {
            text: "Extensions & Integration",
            collapsed: false,
            items: [
              { text: "Index", link: "/guide/extensions-integration/" },
              {
                text: "Model Adapters",
                link: "/guide/extensions-integration/adapters",
              },
              {
                text: "MCP Servers",
                link: "/guide/extensions-integration/mcp-server",
              },
              {
                text: "Custom Tokenizers",
                link: "/guide/extensions-integration/tokenizer",
              },
              {
                text: "Custom Tools",
                link: "/guide/extensions-integration/tools",
              },
            ],
          },
          {
            text: "Agent Engineering",
            collapsed: false,
            items: [
              { text: "Index", link: "/guide/agent-engineering/" },
              {
                text: "Jinja2 Templates",
                link: "/guide/agent-engineering/jinja2-templates",
              },
              {
                text: "Prompt Engineering",
                link: "/guide/agent-engineering/prompt-engineering",
              },
              {
                text: "Troubleshooting",
                link: "/guide/agent-engineering/troubleshooting",
              },
            ],
          },
          {
            text: "Advanced",
            collapsed: false,
            items: [
              { text: "Index", link: "/guide/advanced/" },
              {
                text: "AmritaSense Overview",
                link: "/guide/advanced/amrita-sense-overview",
              },
              {
                text: "The Step Loop",
                link: "/guide/advanced/step-loop",
              },
              {
                text: "Suspend & Resume",
                link: "/guide/advanced/suspend",
              },
              {
                text: "Workflow Debugging",
                link: "/guide/advanced/workflow-debugging",
              },
              {
                text: "Workflow Engine",
                link: "/guide/advanced/workflow-engine",
              },
            ],
          },
          {
            text: "Built-in Capabilities",
            collapsed: false,
            items: [{ text: "Built-in Capabilities", link: "/guide/builtins" }],
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
            text: "Appendix & Design Philosophy",
            collapsed: false,
            items: [
              {
                text: "Appendix & Design Philosophy",
                link: "/guide/appendix",
              },
            ],
          },
          {
            text: "Project Introduction",
            collapsed: false,
            items: [
              {
                text: "Project Introduction",
                link: "/guide/introduction",
              },
            ],
          },
          {
            text: "API Reference",
            collapsed: true,
            items: [
              { text: "Index", link: "/guide/api-reference/" },
              {
                text: "AbilityBackend",
                link: "/guide/api-reference/classes/AbilityBackend",
              },
              {
                text: "AbilityContext",
                link: "/guide/api-reference/classes/AbilityContext",
              },
              {
                text: "AgentRunState",
                link: "/guide/api-reference/classes/AgentRunState",
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
                text: "AmritaConfig",
                link: "/guide/api-reference/classes/AmritaConfig",
              },
              {
                text: "BackendSlots",
                link: "/guide/api-reference/classes/BackendSlots",
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
                text: "BaseTokenizer",
                link: "/guide/api-reference/classes/BaseTokenizer",
              },
              {
                text: "ChatManager",
                link: "/guide/api-reference/classes/ChatManager",
              },
              {
                text: "ChatObject",
                link: "/guide/api-reference/classes/ChatObject",
              },
              {
                text: "ChatObjectMeta",
                link: "/guide/api-reference/classes/ChatObjectMeta",
              },
              {
                text: "ClientManager",
                link: "/guide/api-reference/classes/ClientManager",
              },
              {
                text: "CompletionEvent",
                link: "/guide/api-reference/classes/CompletionEvent",
              },
              {
                text: "CookieConfig",
                link: "/guide/api-reference/classes/CookieConfig",
              },
              {
                text: "DAGNode",
                link: "/guide/api-reference/classes/DAGNode",
              },
              {
                text: "DatabackendOptions",
                link: "/guide/api-reference/classes/DatabackendOptions",
              },
              {
                text: "EmbeddingChunk",
                link: "/guide/api-reference/classes/EmbeddingChunk",
              },
              {
                text: "FallbackContext",
                link: "/guide/api-reference/classes/FallbackContext",
              },
              {
                text: "FunctionConfig",
                link: "/guide/api-reference/classes/FunctionConfig",
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
                text: "LLMConfig",
                link: "/guide/api-reference/classes/LLMConfig",
              },
              {
                text: "LegacyBackend",
                link: "/guide/api-reference/classes/LegacyBackend",
              },
              {
                text: "MCPClient",
                link: "/guide/api-reference/classes/MCPClient",
              },
              {
                text: "MemoryBackend",
                link: "/guide/api-reference/classes/MemoryBackend",
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
                text: "ModelAdapter",
                link: "/guide/api-reference/classes/ModelAdapter",
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
                text: "MultiClientManager",
                link: "/guide/api-reference/classes/MultiClientManager",
              },
              {
                text: "MultiPresetManager",
                link: "/guide/api-reference/classes/MultiPresetManager",
              },
              {
                text: "MultiToolsManager",
                link: "/guide/api-reference/classes/MultiToolsManager",
              },
              {
                text: "NoActionAgentStrategy",
                link: "/guide/api-reference/classes/NoActionAgentStrategy",
              },
              {
                text: "PreCompletionEvent",
                link: "/guide/api-reference/classes/PreCompletionEvent",
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
                text: "RequestMetadata",
                link: "/guide/api-reference/classes/RequestMetadata",
              },
              {
                text: "SendMessageWrap",
                link: "/guide/api-reference/classes/SendMessageWrap",
              },
              {
                text: "StateContext",
                link: "/guide/api-reference/classes/StateContext",
              },
              {
                text: "StepEvents",
                link: "/guide/api-reference/classes/StepEvents",
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
                text: "TextContent",
                link: "/guide/api-reference/classes/TextContent",
              },
              {
                text: "ThinkingConfig",
                link: "/guide/api-reference/classes/ThinkingConfig",
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
                text: "ToolData",
                link: "/guide/api-reference/classes/ToolData",
              },
              {
                text: "ToolFunctionSchema",
                link: "/guide/api-reference/classes/ToolFunctionSchema",
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
        ],
        footer: {
          message: `Apache 2.0 License`,
          copyright: `© AmritaConstant 2025-${new Date().getFullYear()}`,
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
      head: [["link", { rel: "icon", href: "/Amrita.png" }]],
      themeConfig: {
        siteTitle: "Amrita Core 文档",
        nav: [
          { text: "首页", link: "/zh/" },
          { text: "开始", link: "/zh/guide/introduction" },
        ],
        logo: "/Amrita.png",
        sidebar: [
          {
            text: "快速开始",
            collapsed: false,
            items: [
              { text: "索引", link: "/zh/guide/getting-started/" },
              {
                text: "基础示例",
                link: "/zh/guide/getting-started/basic-example",
              },
              {
                text: "最小示例",
                link: "/zh/guide/getting-started/minimal-example",
              },
            ],
          },
          {
            text: "教程",
            collapsed: false,
            items: [
              { text: "索引", link: "/zh/guide/tutorials/" },
              {
                text: "创建你的第一个 Agent",
                link: "/zh/guide/tutorials/chat-object",
              },
              { text: "事件与钩子", link: "/zh/guide/tutorials/event-hooks" },
              { text: "记忆与会话", link: "/zh/guide/tutorials/memory" },
              { text: "流式与回调", link: "/zh/guide/tutorials/streaming" },
              { text: "给 Agent 添加工具", link: "/zh/guide/tutorials/tools" },
            ],
          },
          {
            text: "核心概念",
            collapsed: false,
            items: [
              { text: "索引", link: "/zh/guide/concepts/" },
              { text: "Agent 策略", link: "/zh/guide/concepts/agent-strategy" },
              {
                text: "ChatObject——生命周期管理器",
                link: "/zh/guide/concepts/chat-object",
              },
              { text: "配置系统", link: "/zh/guide/concepts/configuration" },
              { text: "数据管理", link: "/zh/guide/concepts/data" },
              { text: "数据后端", link: "/zh/guide/concepts/data-backend" },
              { text: "记忆模型", link: "/zh/guide/concepts/data-memory" },
              { text: "事件系统", link: "/zh/guide/concepts/event" },
              { text: "工具系统", link: "/zh/guide/concepts/tool" },
            ],
          },
          {
            text: "扩展与集成",
            collapsed: false,
            items: [
              { text: "索引", link: "/zh/guide/extensions-integration/" },
              {
                text: "模型适配器",
                link: "/zh/guide/extensions-integration/adapters",
              },
              {
                text: "MCP 服务器",
                link: "/zh/guide/extensions-integration/mcp-server",
              },
              {
                text: "自定义 Tokenizer",
                link: "/zh/guide/extensions-integration/tokenizer",
              },
              {
                text: "自定义工具",
                link: "/zh/guide/extensions-integration/tools",
              },
            ],
          },
          {
            text: "代理工程",
            collapsed: false,
            items: [
              { text: "索引", link: "/zh/guide/agent-engineering/" },
              {
                text: "Jinja2 模板",
                link: "/zh/guide/agent-engineering/jinja2-templates",
              },
              {
                text: "提示词工程",
                link: "/zh/guide/agent-engineering/prompt-engineering",
              },
              {
                text: "异常排查",
                link: "/zh/guide/agent-engineering/troubleshooting",
              },
            ],
          },
          {
            text: "进阶",
            collapsed: false,
            items: [
              { text: "索引", link: "/zh/guide/advanced/" },
              {
                text: "AmritaSense 概览",
                link: "/zh/guide/advanced/amrita-sense-overview",
              },
              { text: "Step 循环", link: "/zh/guide/advanced/step-loop" },
              { text: "挂起与恢复", link: "/zh/guide/advanced/suspend" },
              {
                text: "工作流调试",
                link: "/zh/guide/advanced/workflow-debugging",
              },
              {
                text: "工作流引擎",
                link: "/zh/guide/advanced/workflow-engine",
              },
            ],
          },
          {
            text: "内置能力",
            collapsed: false,
            items: [{ text: "内置能力", link: "/zh/guide/builtins" }],
          },
          {
            text: "安全机制",
            collapsed: false,
            items: [
              { text: "安全机制", link: "/zh/guide/security-mechanisms" },
            ],
          },
          {
            text: "附录与设计哲学",
            collapsed: false,
            items: [{ text: "附录与设计哲学", link: "/zh/guide/appendix" }],
          },
          {
            text: "项目介绍",
            collapsed: false,
            items: [{ text: "项目介绍", link: "/zh/guide/introduction" }],
          },
          {
            text: "API 参考",
            collapsed: true,
            items: [
              { text: "Index", link: "/zh/guide/api-reference/" },
              {
                text: "AbilityBackend",
                link: "/zh/guide/api-reference/classes/AbilityBackend",
              },
              {
                text: "AbilityContext",
                link: "/zh/guide/api-reference/classes/AbilityContext",
              },
              {
                text: "AgentRunState",
                link: "/zh/guide/api-reference/classes/AgentRunState",
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
                text: "AmritaConfig",
                link: "/zh/guide/api-reference/classes/AmritaConfig",
              },
              {
                text: "BackendSlots",
                link: "/zh/guide/api-reference/classes/BackendSlots",
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
                text: "BaseTokenizer",
                link: "/zh/guide/api-reference/classes/BaseTokenizer",
              },
              {
                text: "ChatManager",
                link: "/zh/guide/api-reference/classes/ChatManager",
              },
              {
                text: "ChatObject",
                link: "/zh/guide/api-reference/classes/ChatObject",
              },
              {
                text: "ChatObjectMeta",
                link: "/zh/guide/api-reference/classes/ChatObjectMeta",
              },
              {
                text: "ClientManager",
                link: "/zh/guide/api-reference/classes/ClientManager",
              },
              {
                text: "CompletionEvent",
                link: "/zh/guide/api-reference/classes/CompletionEvent",
              },
              {
                text: "CookieConfig",
                link: "/zh/guide/api-reference/classes/CookieConfig",
              },
              {
                text: "DAGNode",
                link: "/zh/guide/api-reference/classes/DAGNode",
              },
              {
                text: "DatabackendOptions",
                link: "/zh/guide/api-reference/classes/DatabackendOptions",
              },
              {
                text: "EmbeddingChunk",
                link: "/zh/guide/api-reference/classes/EmbeddingChunk",
              },
              {
                text: "FallbackContext",
                link: "/zh/guide/api-reference/classes/FallbackContext",
              },
              {
                text: "FunctionConfig",
                link: "/zh/guide/api-reference/classes/FunctionConfig",
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
                text: "LLMConfig",
                link: "/zh/guide/api-reference/classes/LLMConfig",
              },
              {
                text: "LegacyBackend",
                link: "/zh/guide/api-reference/classes/LegacyBackend",
              },
              {
                text: "MCPClient",
                link: "/zh/guide/api-reference/classes/MCPClient",
              },
              {
                text: "MemoryBackend",
                link: "/zh/guide/api-reference/classes/MemoryBackend",
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
                text: "ModelAdapter",
                link: "/zh/guide/api-reference/classes/ModelAdapter",
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
                text: "MultiClientManager",
                link: "/zh/guide/api-reference/classes/MultiClientManager",
              },
              {
                text: "MultiPresetManager",
                link: "/zh/guide/api-reference/classes/MultiPresetManager",
              },
              {
                text: "MultiToolsManager",
                link: "/zh/guide/api-reference/classes/MultiToolsManager",
              },
              {
                text: "NoActionAgentStrategy",
                link: "/zh/guide/api-reference/classes/NoActionAgentStrategy",
              },
              {
                text: "PreCompletionEvent",
                link: "/zh/guide/api-reference/classes/PreCompletionEvent",
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
                text: "RequestMetadata",
                link: "/zh/guide/api-reference/classes/RequestMetadata",
              },
              {
                text: "SendMessageWrap",
                link: "/zh/guide/api-reference/classes/SendMessageWrap",
              },
              {
                text: "StateContext",
                link: "/zh/guide/api-reference/classes/StateContext",
              },
              {
                text: "StepEvents",
                link: "/zh/guide/api-reference/classes/StepEvents",
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
                text: "TextContent",
                link: "/zh/guide/api-reference/classes/TextContent",
              },
              {
                text: "ThinkingConfig",
                link: "/zh/guide/api-reference/classes/ThinkingConfig",
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
                text: "ToolData",
                link: "/zh/guide/api-reference/classes/ToolData",
              },
              {
                text: "ToolFunctionSchema",
                link: "/zh/guide/api-reference/classes/ToolFunctionSchema",
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
        ],
        footer: {
          message: `Apache 2.0 许可证(一些内容可能没有完全翻译成中文，请以英文文档为准。)`,
          copyright: `© 弋恒常量 2025-${new Date().getFullYear()}`,
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
