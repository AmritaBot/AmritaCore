# 附录和资源

## 9.1 术语表和术语

### 9.1.1 Agent（智能体）

一个能够感知环境、做出决策并采取行动以实现特定目标的自主程序。在 AmritaCore 中，智能体可以与用户交互、调用工具并管理复杂任务。

### 9.1.2 Token（子词）

语言模型处理和生成的文本单元。Token 可以短至一个字符，也可以长至一个单词（例如，"a"，"hello"，"123"）。管理 Token 的使用对于性能和成本效率至关重要。

### 9.1.3 Prompt（提示词）

提供给语言模型以指导其响应的输入文本。精心制作的提示词会产生更好、更相关的输出。在 AmritaCore 中，提示词包括系统消息、用户输入和上下文信息。

### 9.1.4 Memory（记忆）

AI 系统保留和访问先前交互信息的机制。AmritaCore 的记忆系统管理对话历史和上下文，以实现连贯的多轮对话。

### 9.1.5 LLM（大语言模型）

大语言模型 - 在大量文本上训练的复杂 AI 系统，用于理解和生成类似人类的语言。例子包括 GPT、Claude 和其他基于 Transformer 的模型。

### 9.1.6 MCP（模型上下文协议）

模型上下文协议 - 将工具和数据源连接到 AI 模型的标准。MCP 允许模型以结构化的方式与外部系统交互，将其功能扩展到训练数据之外。

### 9.1.7 其他核心术语

- **上下文窗口**：模型一次可以处理的最大文本量（以 token 计）
- **流式传输**：在生成时分块传递响应，而不是等待完整响应
- **工具调用**：智能体调用外部函数以执行特定任务的能力
- **事件系统**：在各个阶段拦截和修改处理管道的机制
- **会话**：具有自己记忆和状态的隔离对话线程
- **配置**：控制 AmritaCore 在不同场景下如何运行的设置

### 9.1.8 缩写词

- API：应用程序编程接口
- JSON：JavaScript 对象表示法
- HTTP：超文本传输协议
- SSL/TLS：安全套接字层/传输层安全
- REST：表述性状态传递
- SDK：软件开发工具包

## 9.2 项目资源

### 9.2.1 GitHub 仓库链接

- **仓库**：[https://github.com/AmritaBot/AmritaCore](https://github.com/AmritaBot/AmritaCore)
- **问题报告**：在 GitHub 仓库中报告错误并请求功能
- **拉取请求**：欢迎通过拉取请求贡献代码

### 9.2.2 官方网站

- **网站**：[https://amrita-core.suggar.top](https://amrita-core.suggar.top)（即此页面）
- **文档**：全面的指南和教程
- **社区论坛**：与其他用户和开发人员联系

### 9.2.3 贡献指南

欢迎对 AmritaCore 做出贡献。以下是您可以贡献的方法：

1. **Fork 仓库**：创建项目的副本
2. **创建分支**：在新分支中进行更改
3. **编写测试**：确保您的更改不会破坏现有功能
4. **更新文档**：保持文档最新
5. **提交拉取请求**：描述您的更改并提交审核

**代码风格指南**：

- 遵循 PEP 8 Python 风格指南
- 为所有公共函数和类编写文档字符串
- 为所有函数参数和返回值使用类型提示
- 保持函数集中和简洁
- 编写有意义的提交消息

更多信息请参考项目仓库的 `CONTRIBUTING.md` 文件。

## 9.3 社区和支持

### 9.3.1 讨论论坛

- **GitHub 讨论**：使用 GitHub 仓库中的讨论标签页
- **Discord 服务器**：加入我们的社区聊天（在仓库中有链接）
- **Stack Overflow**：将问题标记为 "amrita-core"

### 9.3.2 问题提交

报告问题时：

1. 搜索现有问题以避免重复
2. 提供清晰、描述性的标题
3. 包括重现步骤
4. 分享相关代码片段
5. 指定您的环境（操作系统、Python 版本、AmritaCore 版本）
6. 包括任何相关的错误消息

### 9.3.3 许可证信息 (MIT-3.0)

AmritaCore 根据 MIT 许可证发布。

**许可**

允许任何使用本软件的人，包括商业用途，在 MIT 许可下使用。

有关完整许可证文本，请参阅仓库中的 `LICENSE` 文件。

### 9.3.4 行为准则

我们的社区遵循贡献者盟约行为准则：

- **尊重他人**：无论背景如何，都要尊重每个人
- **建设性**：提供建设性的反馈和建议
- **包容**：欢迎来自各种背景的人
- **关注质量**：努力提高项目质量

## 9.4 相关资源链接

### 9.4.1 LLM 文档链接

- **DeepSeek AI API 文档**：[https://api-docs.deepseek.com/](https://api-docs.deepseek.com/)
- **OpenAI API 文档**：[https://platform.openai.com/docs/](https://platform.openai.com/docs/)
- **Anthropic Claude 文档**：[https://docs.anthropic.com/claude/](https://docs.anthropic.com/claude/)
- **Google AI 文档**：[https://ai.google.dev/](https://ai.google.dev/)
- **Hugging Face 模型**：[https://huggingface.co/models](https://huggingface.co/models)

### 9.4.2 Python 教程

- **官方 Python 教程**：[https://docs.python.org/3/tutorial/](https://docs.python.org/3/tutorial/)
- **Real Python**：[https://realpython.com/](https://realpython.com/)
- **Python 类型提示指南**：[https://mypy.readthedocs.io/en/stable/kinds_of_types.html](https://mypy.readthedocs.io/en/stable/kinds_of_types.html)
- **Python 中的 Async/Await**：[https://docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)

### 9.4.3 异步编程指南

- **Python AsyncIO 文档**：[https://docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)
- **适用于工作 Python 开发者的 AsyncIO**：[https://github.com/gaogaotiantian/asynciolib](https://github.com/gaogaotiantian/asynciolib)
- **理解 Asyncio**：[https://www.roguelynn.com/words/understanding-asyncio/](https://www.roguelynn.com/words/understanding-asyncio/)

### 9.4.4 其他参考资源

- **Pydantic 文档**：[https://docs.pydantic.dev/](https://docs.pydantic.dev/)
- **FastAPI 文档**：[https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)（用于 API 集成示例）
- **使用嵌入进行语义搜索**：[https://platform.openai.com/docs/guides/embeddings](https://platform.openai.com/docs/guides/embeddings)
- **提示工程指南**：[https://www.promptingguide.ai/](https://www.promptingguide.ai/)
