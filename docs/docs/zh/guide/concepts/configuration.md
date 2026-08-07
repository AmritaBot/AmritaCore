# 配置系统

所有运行时设置都在 **`AmritaConfig`** 中——一个你创建一次并传给
`create_agent()` / `ChatObject`（或设为全局）的对象。

## 配置树

| 字段                                  | 用途                                         |
| ------------------------------------- | -------------------------------------------- |
| `llm`（`LLMConfig`）                  | 模型设置：流式、温度、记忆摘要、thinking     |
| `function_config`（`FunctionConfig`） | 工具调用：上限、最小上下文、中间消息         |
| `builtin`（`BuiltinAgentConfig`）     | Agent 行为：工具调用模式、思考模式、停滞触发 |
| `cookie`（`CookieConfig`）            | Cookie 安全检测                              |

## 全局 vs 每次调用

```python
from amrita_core import minimal_init
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig

config = AmritaConfig(
    function_config=FunctionConfig(agent_tool_call_limit=15),
    llm=LLMConfig(stream=True),
)
await minimal_init(config)  # 全局默认

agent = create_agent(..., config=config)  # 或按 agent
```

`get_config()` 返回全局配置；`set_config()` 替换它。

## 影响 Agent 行为的关键设置

| 设置                                    | 默认      | 效果                                               |
| --------------------------------------- | --------- | -------------------------------------------------- |
| `function_config.agent_tool_call_limit` | —         | 每次运行的硬性工具轮次上限                         |
| `builtin.tool_calling_mode`             | `"agent"` | `"agent"` / `"rag"` / `"none"`                     |
| `builtin.agent_thought_mode`            | —         | `"reasoning"` / `"reasoning-required"`（显式推理） |
| `builtin.loop_reasoning_trigger`        | —         | 停滞检测：N 个相同工具签名 → 放弃                  |
| `llm.enable_memory_abstract`            | `False`   | 长历史自动摘要                                     |
| `llm.memory_abstract_threshold`         | —         | 摘要的 token 阈值                                  |

## Preset

`ModelPreset` 打包了端点 + 模型 + `ThinkingConfig` + 工具，由数据后端按会话
加载。`create_agent()` 根据你的 `base_url` / `api_key` / `model` 参数构建
一个；高级场景用 `MultiPresetManager` 按会话提供不同 preset
（见[数据层](data.md)）。

## 下一步

[事件系统](event.md)——处理管线的钩子。
