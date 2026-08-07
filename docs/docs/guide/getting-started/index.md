# Getting Started

Welcome! This section gets you from zero to a running agent as fast as possible.

## Before You Start

- **Python 3.10+** (up to 3.14)
- **An LLM API endpoint** — OpenAI-compatible, Anthropic, or any [supported adapter](../extensions-integration/adapters.md)
- A few MB of RAM for the framework itself (context memory grows with your session)

No prior knowledge of AmritaSense is required for this section — everything you
need is covered inline.

## Install

We recommend `uv` for environment management:

```bash
uv init
uv venv
uv add amrita-core
```

Or with pip:

```bash
pip install amrita-core
```

Working directly from the source repository? Clone it and `pip install -e .`
(see the repo `README.md`).

## What's Next

1. [Minimal Example](minimal-example.md) — a 10-line runnable agent
2. [Basic Example](basic-example.md) — streaming, tools and sessions in one place
3. Then follow the [Tutorials](../tutorials/index.md) to build up systematically
