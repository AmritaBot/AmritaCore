# 快速开始

欢迎！本节带你从零到第一个可运行的 agent，用最短路径。

## 开始之前

- **Python 3.10+**（最高 3.14）
- **一个 LLM API 端点**——OpenAI 兼容、Anthropic 或任意[受支持适配器](../extensions-integration/adapters.md)
- 少量内存（框架本身很小；上下文记忆随会话增长）

本节不需要任何 AmritaSense 前置知识——所需内容均内联覆盖。

## 安装

推荐使用 `uv` 管理环境：

```bash
uv init
uv venv
uv add amrita-core
```

或用 pip：

```bash
pip install amrita-core
```

直接从源码仓库开发？Clone 后 `pip install -e .`（见仓库 `README.md`）。

## 下一步

1. [最小示例](minimal-example.md) —— 一个 10 行的可运行 agent
2. [基础示例](basic-example.md) —— 流式、工具与会话一站式
3. 然后跟随[教程](../tutorials/index.md)系统化构建
