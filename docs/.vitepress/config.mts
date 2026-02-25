import { defineConfig } from "vitepress";
import { withMermaid } from "vitepress-plugin-mermaid";

// https://vitepress.dev/reference/site-config
export default withMermaid({
  lastUpdated: true,
  ignoreDeadLinks: true,
  locales: {
    root: {
      label: "English",
      lang: "en-US",
      title: "Amrita",
      description: "Amrita Core",
      head: [
        // Icon
        [
          "link",
          {
            rel: "icon",
            href: "/Amrita.png",
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
                text: "BaseModel",
                link: "/guide/api-reference/classes/BaseModel",
              },
              {
                text: "ChatObject",
                link: "/guide/api-reference/classes/ChatObject",
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
                text: "Function",
                link: "/guide/api-reference/classes/Function",
              },
              {
                text: "FunctionDefinitionSchema",
                link: "/guide/api-reference/classes/FunctionDefinitionSchema",
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
      title: "Amrita",
      description: "Amrita 核心",
      head: [
        [
          "link",
          {
            rel: "icon",
            href: "/Amrita.png",
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
                text: "BaseModel",
                link: "/zh/guide/api-reference/classes/BaseModel",
              },
              {
                text: "ChatObject",
                link: "/zh/guide/api-reference/classes/ChatObject",
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
                text: "Function",
                link: "/zh/guide/api-reference/classes/Function",
              },
              {
                text: "FunctionDefinitionSchema",
                link: "/zh/guide/api-reference/classes/FunctionDefinitionSchema",
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
