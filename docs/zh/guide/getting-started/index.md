# 开始使用

## 环境准备

### 2.1.1 系统要求

要使用 AmritaCore，您需要：

- Python 3.10 或更高版本（最高到 3.14）
- 足够的 RAM 来处理上下文内存（建议项目至少 1GB）
- 互联网连接以连接到 LLM API
- 访问 LLM 提供商（OpenAI、Azure OpenAI 或兼容服务）

### 2.1.2 Python 版本支持

AmritaCore 官方支持从 3.10 到 3.14 的 Python 版本。虽然它可能在其他版本上也能工作，但这些是经过测试和推荐的版本。

### 2.1.3 依赖安装

我们建议使用虚拟环境进行开发，可使用 `uv`、`pdm` 等。

```bash
uv init
uv venv
uv add amrita-core
```


使用 pip 安装 AmritaCore：

```bash
pip install amrita-core
```

或者如果您直接使用源代码：

```bash
git clone https://github.com/AmritaBot/AmritaCore.git
cd AmritaCore
pip install -e .
```

### 2.1.4 代码示例

您可以在仓库路径 `/demo` 中查看更多示例。