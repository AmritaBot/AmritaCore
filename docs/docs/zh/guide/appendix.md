# 附录与资源

## 术语表

### Agent

一个自主程序，感知环境、做出决策并采取行动以实现特定目标。在 AmritaCore 中，agent 可以与用户交互、调用工具并管理复杂任务。

### Token

语言模型处理和生成的文本单位。Token 可以短至一个字符，也可长至一个单词（如 "a"、"hello"、"123"）。管理 token 使用对性能和成本效率至关重要。

### Prompt

提供给语言模型以指导其响应的输入文本。精心设计的提示词能产生更好、更相关的输出。在 AmritaCore 中，提示词包括系统消息、用户输入和上下文信息。

### Memory

AI 系统保留和访问先前交互信息的机制。AmritaCore 的记忆系统管理对话历史和上下文，以实现连贯的多轮对话。

### LLM

大语言模型——基于海量文本训练的复杂 AI 系统，用于理解和生成类人语言。例如 GPT、Claude 和其他基于 transformer 的模型。

### MCP

Model Context Protocol——将工具和数据源连接到 AI 模型的标准协议。MCP 允许模型以结构化方式与外部系统交互，扩展其在训练数据之外的能力。

### 其他核心术语

- **上下文窗口**：模型一次能处理的最大文本量（以 token 计）
- **流式传输**：在生成响应时以块的形式传递，而非等待完整响应
- **工具调用**：agent 调用外部函数执行特定任务的能力
- **事件系统**：在处理管道的各个阶段拦截和修改处理流程的机制
- **会话**：具有独立记忆和状态的隔离对话线程
- **配置**：控制 AmritaCore 在不同场景下行为的设置
- **工作流引擎**：自 v0.9.0rc1 起驱动 ChatObject 执行的可组合节点图系统。节点通过 `>>` 连接，由 `WorkflowInterpreter` 执行。由 `amrita-sense` 包提供。
- **StrategyLikedObject**：有状态 agent 策略实例的抽象基类。与 `AgentStrategy`（作为类型传递）不同，`StrategyLikedObject` 作为预初始化实例传递，支持内部状态机和资源管理。
- **预组合工作流**：可直接传递给 `ChatObject(workflow=...)` 的即用型 `NodeComposeRendered` 管道图。位于 `amrita_core.builtins.workflows`（如 `SIMPLE_REACT`、`SIMPLE_CHAT`）。
- **DI 资源字段**：`StrategyContext` 上的依赖注入资源字段（如 `preset`、`config`、`io_stream`），直接将框架服务传递给 agent 策略，无需通过 `ChatObject` 路由。
- **提示工程**：设计和改进提示词（系统消息、模板、指令）以引导 LLM 产生期望输出的实践。

### 缩写

- API：应用程序编程接口
- JSON：JavaScript 对象表示法
- HTTP：超文本传输协议
- SSL/TLS：安全套接字层/传输层安全
- REST：表述性状态转移
- SDK：软件开发工具包

## 项目资源

### GitHub 仓库

- **仓库**：[https://github.com/AmritaBot/AmritaCore](https://github.com/AmritaBot/AmritaCore)
- **问题报告**：在 GitHub 仓库中报告 bug 和请求功能
- **Pull Request**：欢迎通过 Pull Request 贡献

### 官方网站

- **AmritaCore 网站**：[https://core.amritabot.com](https://core.amritabot.com)（本站）
- **amrita-sense 网站**：[https://sense.amritabot.com](https://sense.amritabot.com)——共享基础设施包的文档

### 贡献指南

欢迎对 AmritaCore 做出贡献：

1. **Fork 仓库**
2. **创建分支**
3. **编写测试**
4. **更新文档**
5. **提交 Pull Request**

**代码风格指南**：

- 遵循 PEP 8 Python 风格指南
- 为所有公共函数和类编写文档字符串
- 为所有函数参数和返回值使用类型提示
- 保持函数专注且简洁

### 许可证信息（Apache 2.0）

AmritaCore 在 Apache 2.0 许可证下发布。完整许可证文本请参阅仓库中的 `LICENSE` 文件。

### 行为准则

我们的社区遵循 Contributor Covenant 行为准则：

- **互相尊重**：无论背景如何，尊重每个人
- **建设性反馈**：提供建设性的反馈和建议
- **包容性**：欢迎来自各种背景的人
- **注重质量**：努力提升项目质量

## 相关资源

### LLM 文档链接

- **DeepSeek AI API 文档**：[https://api-docs.deepseek.com/](https://api-docs.deepseek.com/)
- **OpenAI API 文档**：[https://platform.openai.com/docs/](https://platform.openai.com/docs/)
- **Anthropic Claude 文档**：[https://docs.anthropic.com/claude/](https://docs.anthropic.com/claude/)
- **Google AI 文档**：[https://ai.google.dev/](https://ai.google.dev/)
- **Hugging Face 模型**：[https://huggingface.co/models](https://huggingface.co/models)

### Python 教程

- **Python 官方教程**：[https://docs.python.org/3/tutorial/](https://docs.python.org/3/tutorial/)
- **Real Python**：[https://realpython.com/](https://realpython.com/)
- **Python 类型提示指南**：[https://mypy.readthedocs.io/en/stable/kinds_of_types.html](https://mypy.readthedocs.io/en/stable/kinds_of_types.html)
- **Python 中的 Async/Await**：[https://docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)

### 异步编程指南

- **Python AsyncIO 文档**：[https://docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)
- **面向工作 Python 开发者的 AsyncIO**：[https://github.com/gaogaotiantian/asynciolib](https://github.com/gaogaotiantian/asynciolib)
- **理解 Asyncio**：[https://www.roguelynn.com/words/understanding-asyncio/](https://www.roguelynn.com/words/understanding-asyncio/)

### 其他参考资源

- **Pydantic 文档**：[https://docs.pydantic.dev/](https://docs.pydantic.dev/)
- **FastAPI 文档**：[https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)（用于 API 集成示例）
- **使用 Embeddings 进行语义搜索**：[https://platform.openai.com/docs/guides/embeddings](https://platform.openai.com/docs/guides/embeddings)
- **提示工程指南**：[https://www.promptingguide.ai/](https://www.promptingguide.ai/)
