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

| 设置                                      | 默认        | 效果                                                                       |
| ----------------------------------------- | ----------- | -------------------------------------------------------------------------- |
| `function_config.agent_tool_call_limit`   | `10`        | 每次运行的硬性工具轮次上限                                                 |
| `function_config.agent_step_token_budget` | `-1`        | 每 Step prompt-token 预算（`<= 0` = 禁用/不限）                            |
| `builtin.tool_calling_mode`               | `"agent"`   | `"agent"` / `"rag"` / `"none"`                                             |
| `builtin.agent_thought_mode`              | `"chat"`    | `"reasoning"` / `"chat"` / `"reasoning-required"` / `"reasoning-optional"` |
| `builtin.loop_reasoning_trigger`          | `5`         | 停滞检测：N 个相同工具签名 → 放弃                                          |
| `llm.context_strategy`                    | `"compact"` | 历史超预算后的处理方式：`"compact"` / `"slide"` / `"none"`                 |
| `llm.compaction_trigger_ratio`            | `0.9`       | 触发历史管理时占注意力窗口的比例                                           |
| `llm.slide_target_ratio`                  | `0.7`       | `"slide"` 下将历史裁剪到的窗口比例                                         |
| `preset.max_context`                      | `None`      | 按模型的输入预算；未设置时回退到 `llm.session_tokens_windows`（64k）       |
| `preset.max_output`                       | `28000`     | 按模型的响应预留；`llm.max_tokens`（10000）为最后兜底                      |
| `llm.memory_length_limit`                 | `200`       | 消息条数兜底，即使不上报 usage 也会触发（`0` = 关闭）                      |
| `llm.enable_overflow_recovery`            | `True`      | provider 因请求过大拒绝时，压缩并重试一次                                  |

## Preset

`ModelPreset` 打包了端点 + 模型 + `ThinkingConfig` + 工具，由数据后端按会话
加载。`create_agent()` 根据你的 `base_url` / `api_key` / `model` 参数构建
一个；高级场景用 `MultiPresetManager` 按会话提供不同 preset
（见[数据层](data.md)）。

### 注意力窗口属于预设

输入预算与响应预留属于**模型**，而不是某个全局设置：

```python
from amrita_core import ModelPreset

preset = ModelPreset(
    model="deepseek-chat",
    name="deepseek",
    api_key="sk-...",
    max_context=64_000,  # 输入预算
    max_output=8_000,  # 为响应预留的 token
)
```

`max_context` + `max_output` 就是模型的注意力窗口——相当于 Copilot 里的
"为响应保留"。`LLMConfig.session_tokens_windows` 与 `LLMConfig.max_tokens`
仅在预设未设置时作为兜底，因此模型的真实上限跟随模型本身。

两个辅助函数负责把预设字段与全局配置合成确定值，调用方无需自行判断 `None`：

```python
from amrita_core.types.preset import resolve_max_context, resolve_max_output

window = resolve_max_context(preset, config)
budget = resolve_max_output(preset, config)
```

模型适配器用 `resolve_max_output` 生成请求的 `max_tokens`，`ContextCompactor`
用 `resolve_max_context` 计算压缩阈值。这就是上表中那两项要成对理解的原因：
窗口驱动压缩触发。

### 计价

预设还可以携带 `rate`，即持有单价的
[`RateConfig`](../api-reference/classes/RateConfig.md)。它会被复制进该预设
生效期间产生的每一条计费记录，因此调价后成本历史仍然可读。这些记录去哪，见
[数据后端](data-backend.md)。

## 下一步

[事件系统](event.md)——处理管线的钩子。
