# API 参考

本参考按功能模块组织。每个条目链接到类页面以获取完整文档。

## 核心 API 函数

### `load_amrita()`

`load_amrita()` 函数在配置中启用 MCP 时异步加载 MCP 客户端。分词器和适配器在导入时已注册——`load_amrita()` 不会加载它们。

```python
import asyncio
from amrita_core import load_amrita

async def main():
    await load_amrita()

asyncio.run(main())
```

**使用说明**：

- 自 v0.9.0rc1 起不再需要先调用 `init()`
- 如果使用自定义配置，应在 `set_config()` 之后调用
- 启用 MCP 时，必须调用 `load_amrita()`

### `minimal_init()`

`minimal_init()` 函数执行最小初始化：应用配置并在启用时加载 MCP 客户端。

```python
from amrita_core import minimal_init

await minimal_init()
```

### `set_config(config)`

`set_config()` 函数将配置应用到 AmritaCore。

```python
from amrita_core.config import AmritaConfig, set_config

config = AmritaConfig()
set_config(config)
```

**参数**：

- `config` ([AmritaConfig](classes/AmritaConfig.md))：要设置的配置对象

### `get_config()`

`get_config()` 函数检索当前的 AmritaCore 配置。

```python
from amrita_core.config import get_config

config = get_config()
print(config.function_config.use_minimal_context)
```

### `create_agent()`

`create_agent()` 工厂函数通过自动创建临时预设来创建 agent。**这是构建 agent 的推荐入口点。**

```python
from amrita_core import create_agent

agent = create_agent(
    "https://api.example.com",
    "your-api-key",
    model="gpt-4",
    model_config={"temperature": 0.7},
)
```

**参数**：

- `base_url` (str)：API 端点 URL
- `api_key` (str)：API 密钥
- `model` (str, optional)：要使用的模型。默认为 `"auto"`
- `train` (str | None, optional)：系统提示词
- `model_config` ([ModelConfig](classes/ModelConfig.md) | dict | None, optional)：模型配置
- `config` ([AmritaConfig](classes/AmritaConfig.md) | None, optional)：agent 配置
- `**kwargs`：转发给 [AgentRuntime](classes/AgentRuntime.md) 的额外参数

**返回**：[AgentRuntime](classes/AgentRuntime.md) - 配置好的 agent 运行时实例

## Step 循环类型（内置 ReAct）

- [AgentRunState](classes/AgentRunState.md)：语义级 step 运行状态（计划、停滞窗口、token）
- [DAGNode](classes/DAGNode.md)：任务计划的子步骤
- [StepEvents](classes/StepEvents.md)：可变 step 生命周期事件（`step_intro` / `step_leave` / `step_iteration` / `tool_call` / `tool_return`）与 `StepAbortError`

完整机制见[进阶 → Step 循环](../advanced/step-loop.md)。
