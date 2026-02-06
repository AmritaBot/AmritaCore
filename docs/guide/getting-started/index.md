# Getting Started

## Environment Preparation

### 2.1.1 System Requirements

To use AmritaCore, you'll need:

- Python 3.10 or higher (up to 3.14)
- Sufficient RAM to handle context memory (minimum 1GB recommended for project.)
- Internet connection for connecting to LLM APIs
- Access to an LLM provider (OpenAI, Azure OpenAI, or compatible service)

### 2.1.2 Python Version Support

AmritaCore officially supports Python versions from 3.10 up to 3.14. While it may work with other versions, these are the tested and recommended versions.

### 2.1.3 Dependency Installation

We recommend using a virtual environment for development by using `uv` , `pdm` etc.

```bash
uv init
uv venv
uv add amrita-core
````


Install AmritaCore using pip:

```bash
pip install amrita-core
```

Or if you're working directly with the source code:

```bash
git clone https://github.com/AmritaBot/AmritaCore.git
cd AmritaCore
pip install -e .
```

### 2.1.4 Code demo

You can view more demo at repo's path `/demo`.
