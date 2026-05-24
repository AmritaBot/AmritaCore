# Appendix and Resources

## 9.1 Glossary and Terminology

### 9.1.1 Agent

An autonomous program that perceives its environment, makes decisions, and takes actions to achieve specific goals. In AmritaCore, agents can interact with users, call tools, and manage complex tasks.

### 9.1.2 Token

A unit of text that language models process and generate. Tokens can be as short as one character or as long as one word (e.g., "a", "hello", "123"). Managing token usage is crucial for performance and cost efficiency.

### 9.1.3 Prompt

Input text provided to a language model to guide its response. Well-crafted prompts lead to better, more relevant outputs. In AmritaCore, prompts include system messages, user inputs, and contextual information.

### 9.1.4 Memory

The mechanism by which an AI system retains and accesses information from previous interactions. AmritaCore's memory system manages conversation history and context to enable coherent multi-turn conversations.

### 9.1.5 LLM

Large Language Model - sophisticated AI systems trained on vast amounts of text to understand and generate human-like language. Examples include GPT, Claude, and other transformer-based models.

### 9.1.6 MCP

Model Context Protocol - a standard for connecting tools and data sources to AI models. MCP allows models to interact with external systems in a structured way, extending their capabilities beyond their training data.

### 9.1.7 Other Core Terms

- **Context Window**: The maximum amount of text (in tokens) that a model can process at once
- **Streaming**: Delivering responses in chunks as they're generated, rather than waiting for the complete response
- **Tool Calling**: The ability for an agent to invoke external functions to perform specific tasks
- **Event System**: A mechanism for intercepting and modifying the processing pipeline at various stages
- **Session**: An isolated conversation thread with its own memory and state
- **Configuration**: Settings that control how AmritaCore behaves in different scenarios
- **Workflow Engine**: A composable node graph system that drives ChatObject execution since v0.9.0rc1. Nodes are connected with `>>` and executed by `WorkflowInterpreter`. Provided by the `amrita-sense` package.
- **StrategyLikedObject**: An abstract base class for stateful agent strategy instances. Unlike `AgentStrategy` (passed as a type), `StrategyLikedObject` is passed as a pre-initialised instance, enabling internal state machines and resource management.

### 9.1.8 Abbreviations

- API: Application Programming Interface
- JSON: JavaScript Object Notation
- HTTP: HyperText Transfer Protocol
- SSL/TLS: Secure Sockets Layer/Transport Layer Security
- REST: Representational State Transfer
- SDK: Software Development Kit

## 9.2 Project Resources

### 9.2.1 GitHub Repository Link

- **Repository**: [https://github.com/AmritaBot/AmritaCore](https://github.com/AmritaBot/AmritaCore)
- **Issue Reporting**: Report bugs and request features in the GitHub repository
- **Pull Requests**: Contributions are welcome through pull requests

### 9.2.2 Official Websites

- **AmritaCore Website**: [https://core.amritabot.com](https://core.amritabot.com) (This site)
- **amrita-sense Website**: [https://sense.amritabot.com](https://sense.amritabot.com) — Documentation for the shared infrastructure package
- **Documentation**: Comprehensive guides and tutorials
- **Community Forum**: Connect with other users and developers

### 9.2.3 Contribution Guidelines

Contributions to AmritaCore are welcome. Here's how you can contribute:

1. **Fork the Repository**: Create your own copy of the project
2. **Create a Branch**: Make your changes in a new branch
3. **Write Tests**: Ensure your changes don't break existing functionality
4. **Update Documentation**: Keep the documentation up to date
5. **Submit a Pull Request**: Describe your changes and submit for review

**Code Style Guidelines**:

- Follow PEP 8 Python style guide
- Write docstrings for all public functions and classes
- Use type hints for all function parameters and return values
- Keep functions focused and concise
- Write meaningful commit messages

For more information, please refer to the `CONTRIBUTING.md` file in the project repository.

## 9.3 Community and Support

### 9.3.1 Discussion Forums

- **GitHub Discussions**: Use the Discussions tab in the GitHub repository
- **Discord Server**: Join our community chat (link in repository)
- **Stack Overflow**: Tag questions with "amrita-core"

### 9.3.2 Issue Submission

When reporting issues:

1. Search existing issues to avoid duplicates
2. Provide a clear, descriptive title
3. Include reproduction steps
4. Share relevant code snippets
5. Specify your environment (OS, Python version, AmritaCore version)
6. Include any relevant error messages

### 9.3.3 License Information (Apache 2.0)

AmritaCore is released under the Apache 2.0 license.

#### Licensing

Permission is hereby granted to any person obtaining a copy of this software and associated documentation files (the "Software"), to use the Software under the Apache 2.0 license, including for commercial purposes.

For the full license text, please refer to the `LICENSE` file in the repository.

### 9.3.4 Code of Conduct

Our community follows the Contributor Covenant Code of Conduct:

- **Be Respectful**: Treat everyone with respect regardless of their background
- **Be Constructive**: Provide constructive feedback and suggestions
- **Be Inclusive**: Welcome people from all backgrounds
- **Focus on Quality**: Strive to improve the quality of the project

## 9.4 Related Resources

### 9.4.1 LLM Documentation Links

- **DeepSeek AI API Documentation**: [https://api-docs.deepseek.com/](https://api-docs.deepseek.com/)
- **OpenAI API Documentation**: [https://platform.openai.com/docs/](https://platform.openai.com/docs/)
- **Anthropic Claude Documentation**: [https://docs.anthropic.com/claude/](https://docs.anthropic.com/claude/)
- **Google AI Documentation**: [https://ai.google.dev/](https://ai.google.dev/)
- **Hugging Face Models**: [https://huggingface.co/models](https://huggingface.co/models)

### 9.4.2 Python Tutorials

- **Official Python Tutorial**: [https://docs.python.org/3/tutorial/](https://docs.python.org/3/tutorial/)
- **Real Python**: [https://realpython.com/](https://realpython.com/)
- **Python Type Hints Guide**: [https://mypy.readthedocs.io/en/stable/kinds_of_types.html](https://mypy.readthedocs.io/en/stable/kinds_of_types.html)
- **Async/Await in Python**: [https://docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)

### 9.4.3 Asynchronous Programming Guides

- **Python AsyncIO Documentation**: [https://docs.python.org/3/library/asyncio.html](https://docs.python.org/3/library/asyncio.html)
- **AsyncIO for Working Python Developers**: [https://github.com/gaogaotiantian/asynciolib](https://github.com/gaogaotiantian/asynciolib)
- **Understanding Asyncio**: [https://www.roguelynn.com/words/understanding-asyncio/](https://www.roguelynn.com/words/understanding-asyncio/)

### 9.4.4 Other Reference Resources

- **Pydantic Documentation**: [https://docs.pydantic.dev/](https://docs.pydantic.dev/)
- **FastAPI Documentation**: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/) (for API integration examples)
- **Semantic Search with Embeddings**: [https://platform.openai.com/docs/guides/embeddings](https://platform.openai.com/docs/guides/embeddings)
- **Prompt Engineering Guide**: [https://www.promptingguide.ai/](https://www.promptingguide.ai/)
