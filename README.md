# AmritaCore

<center><img src="./docs/docs/public/Amrita.png" alt="Logo" width="200" height="200">
<p>
    <a href="https://img.shields.io/pypi/v/amrita-core">
      <img src="https://img.shields.io/pypi/v/amrita-core?color=blue&style=flat-square" alt="PyPI Version">
    </a>
    <a href="https://www.python.org/">
      <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&style=flat-square" alt="Python Version">
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/github/license/AmritaBot/AmritaCore?style=flat-square" alt="License">
    </a>
    <img src="https://img.shields.io/badge/AmritaCore-Soma-blue?style=flat-square" alt="AmritaCore">
    <a href="https://discord.gg/byAD3sbjjj">
      <img src="https://img.shields.io/badge/Discord-Project.Amrita-blue?logo=discord&style=flat-square" alt="Discord">
    </a>
    <a href="https://qm.qq.com/q/9J23pPZN3a">
      <img src="https://img.shields.io/badge/QQ-1006893368-blue?style=flat-square" alt="QQ Group">
    </a>
  </p>

</center>

AmritaCore is a **lightweight Agent runtime** built on top of **AmritaSense**. It delivers native async streaming, tool integration, event hooks, and memory management — everything you need to build interactive, production‑ready Agent applications without the overhead of heavyweight frameworks.

## 🚀 Fast Lookup

```python
import asyncio
from amrita_core import create_agent

async def main():
    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="your-api-key",
        model="gpt-4o-mini",
    )
    chat = agent.get_chatobject("Hello, how are you?")
    print(await chat.full_response())

asyncio.run(main())
```

## 🔑 Key Features

- **Interactive‑first design** — native async streaming with suspend/resume
- **Vendor‑agnostic adapter system** — OpenAI, Anthropic, and extensible
- **Declarative dependency injection** — type‑safe, based on function signatures
- **Event‑driven hooks** — intercept and modify the processing pipeline
- **Tool system** — `@simple_tool`, `@on_tools`, and MCP client support
- **Advanced memory management** — automatic context window and token optimisation

## 📖 Documentation

Full guides, API references, and examples at [core.amritabot.com](https://core.amritabot.com).

## 🤝 Contributing

We welcome contributions! Please see our [contribution guidelines](./CONTRIBUTING.md) for more information.

## 📄 License

This project is licensed under the **Apache 2.0 License** — see the [LICENSE](./LICENSE) file for details. All versions of AmritaCore are released under Apache 2.0.

## Other files

- [CONTRIBUTING.md](./CONTRIBUTING.md) — Contribution guidelines
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) — Code of conduct
- [ZH-CN.md](./readmes/ZH_CN.md) — 简体中文
- [EN-US.md](./readmes/EN_US.md) — English (US)

## Unstable Features

- `Python 3.14+ Supporting`: we are not sure if it will work well on Python 3.14+(No GIL Version).
