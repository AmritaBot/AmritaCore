# 快速开始

## 环境准备

### 系统要求

使用 AmritaCore 需要：

- Python 3.10 及以上（最高 3.14）
- 足够的内存处理上下文记忆（建议至少 1GB）
- 网络连接以访问 LLM API
- 访问 LLM 提供商（OpenAI、Azure OpenAI 或兼容服务）

### Python 版本支持

AmritaCore 官方支持 Python 3.10 至 3.13。其他版本可能也能运行，但以上为经过测试和推荐的版本。

### 安装依赖

建议使用虚拟环境进行开发，推荐使用 `uv`、`pdm` 等工具。

```bash
uv init
uv venv
uv add amrita-core
```

使用 `Amctl`（我们的模板工具，基于 `uv`）创建 AmritaCore 项目：

```bash
# 如果尚未安装 Amctl，先运行以下命令
# pip install amctl
# 或使用 uv：
# uv tool install amctl
amctl create -t amrita_core
```

使用 pip 安装 AmritaCore：

```bash
pip install amrita-core
```

或者直接使用源码：

```bash
git clone https://github.com/AmritaBot/AmritaCore.git
cd AmritaCore
pip install -e .
```

### 代码演示

你可以在仓库的 `/demo` 路径下查看更多演示。
