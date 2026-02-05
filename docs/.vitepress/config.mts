import { defineConfig } from "vitepress";
import { withMermaid } from "vitepress-plugin-mermaid";

// https://vitepress.dev/reference/site-config
export default withMermaid({
  lastUpdated: true,
  ignoreDeadLinks: true,
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
      { text: "Main page", link: "/" },
      // { text: "Start", link: "/amrita" },
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
          { text: "Security Mechanisms", link: "/guide/security-mechanisms" },
        ],
      },
      {
        text: "API Reference",
        collapsed: false,
        items: [
          { text: "Index", link: "/guide/api-reference/" },
          {
            text: "AmritaConfig",
            link: "/guide/api-reference/classes/AmritaConfig",
          },
          { text: "BaseModel", link: "/guide/api-reference/classes/BaseModel" },
          {
            text: "ChatObject",
            link: "/guide/api-reference/classes/ChatObject",
          },
          { text: "Function", link: "/guide/api-reference/classes/Function" },
          {
            text: "FunctionDefinitionSchema",
            link: "/guide/api-reference/classes/FunctionDefinitionSchema",
          },
          {
            text: "MemoryModel",
            link: "/guide/api-reference/classes/MemoryModel",
          },
          { text: "Message", link: "/guide/api-reference/classes/Message" },
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
          { text: "ToolCall", link: "/guide/api-reference/classes/ToolCall" },
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
      { icon: "github", link: "https://github.com/AmritaBot/docs-core" },
    ],
  },
  mermaidPlugin: {
    class: "mermaid my-class", // set additional css classes for parent container
  },
});
