# 数据杂项

本页涵盖支持核心数据容器和后端系统的其他数据类型。

## ModelConfig 模型配置

[`ModelConfig`](../api-reference/classes/ModelConfig.md) 保存 LLM 请求的调优参数：

```python
from amrita_core.types import ModelConfig

model_config = ModelConfig(
    temperature=0.7,
    top_p=0.9,
    top_k=50,
    stream=True,
    multimodal=False,
    cot_model=False,
)
```

| 字段          | 默认值  | 描述                          |
| ------------- | ------- | ----------------------------- |
| `temperature` | `0.6`   | 采样温度                      |
| `top_p`       | `0.8`   | 核采样                        |
| `top_k`       | `50`    | Top-K 采样                    |
| `stream`      | `False` | 启用流式传输                  |
| `multimodal`  | `False` | 启用多模态输入                |
| `cot_model`   | `False` | 从响应中去除 `\<think\>` 标签 |

## ModelPreset 模型预设

[`ModelPreset`](../api-reference/classes/ModelPreset.md) 将模型标识、端点凭据、协议和配置捆绑在一起：

```python
from amrita_core.types import ModelPreset, ModelConfig

preset = ModelPreset(
    model="gpt-4",
    name="my-gpt4",
    base_url="https://api.openai.com/v1",
    api_key="sk-xxx",
    protocol="openai",                    # 适配器协议
    config=ModelConfig(temperature=0.7),
    thinking_config=ThinkingConfig(
        thinking_type="enabled",
        thinking_effort="high",
    ),
)
```

`ModelPreset` 还提供 `load(path)` / `save(path)` 用于 JSON 序列化。

## ThinkingConfig 推理配置

[`ThinkingConfig`](../api-reference/classes/ThinkingConfig.md) 控制支持推理/思考功能的模型的推理行为：

```python
from amrita_core.types import ThinkingConfig

tc = ThinkingConfig(
    thinking_type="enabled",          # "enabled" | "disabled" | None
    enable_thinking=True,
    thinking_effort="high",           # "minimal" | "low" | "medium" | "high" | "xhigh" | "max"
    content_mode="optional",          # "never" | "by-tool" | "optional"
)
```

## PresetManager 预设管理

[`PresetManager`](../api-reference/classes/PresetManager.md) 提供 `ModelPreset` 实例的集中管理。它是一个**单例**——所有会话共享同一个实例：

```python
from amrita_core.preset import PresetManager
from amrita_core.types import ModelPreset, ModelConfig

manager = PresetManager()

manager.add_preset(ModelPreset(
    model="gpt-3.5-turbo", name="fast",
    api_key="sk-xxx", config=ModelConfig(stream=True)
))
manager.add_preset(ModelPreset(
    model="gpt-4", name="smart",
    api_key="sk-xxx"
))

manager.set_default_preset("fast")
preset = manager.get_preset("smart")
default = manager.get_default_preset()  # 自动 fallback
```

**自动 fallback**：如果未设置默认值，`get_default_preset()` 会随机选择一个已注册的预设。使用 `test_presets()` 进行异步连通性检查。

## UniResponse / UniResponseUsage 统一响应

[`UniResponse`](../api-reference/classes/UniResponse.md) 是所有适配器返回的统一响应格式：

```python
from amrita_core.types import UniResponse, UniResponseUsage

response = UniResponse(
    content="您好！我能帮您什么？",
    role="assistant",
    tool_calls=None,
    reasoning_content=None,
    usage=UniResponseUsage(
        prompt_tokens=50,
        completion_tokens=20,
        total_tokens=70,
    ),
)
```

所有适配器的 `call_api` / `call_tools` 方法都产生 `UniResponse` 实例，提供厂商无关的接口。

## SendMessageWrap 消息包装器

[`SendMessageWrap`](../api-reference/classes/SendMessageWrap.md) 包装发送给 LLM 的消息列表。它将系统消息（`train`）、记忆、用户查询和任何附加的结束消息分开：

```python
from amrita_core.types import SendMessageWrap

wrap = SendMessageWrap.validate_messages([
    Message(role="system", content="您是一个有用的助手。"),
    Message(role="user", content="2+2是多少？"),
])

# 按顺序遍历所有消息：
for msg in wrap:
    print(msg.role, msg.content)

# 解包为扁平列表（可选排除系统消息）
flat = wrap.unwrap(exclude_system=False)

# 在用户查询后追加额外消息
wrap.append(Message(role="assistant", content="4"))
```

`SendMessageWrap` 被 `ChatObject` 的 `context_wrap` 和 `StrategyContext.original_context` 内部使用。

## EmbeddingChunk 嵌入结果

[`EmbeddingChunk`](../api-reference/classes/EmbeddingChunk.md) 表示单个嵌入向量：

```python
from amrita_core.types import EmbeddingChunk

chunk = EmbeddingChunk(
    embedding=[0.1, 0.2, 0.3, ...],
    index=0
)
```

由嵌入适配器通过 `call_embed()` 返回。与 OpenAI 的嵌入响应格式兼容。

## register_content 自定义内容类型

可以动态注册新的内容类型：

```python
from amrita_core.types import Content, register_content
from typing import Literal

class MyCustomContent(Content[Literal["my_type"]]):
    type: Literal["my_type"] = "my_type"
    payload: str

register_content(MyCustomContent)
```

注册后，`Message` 验证会自动将 `{"type": "my_type", ...}` 字典反序列化为 `MyCustomContent` 实例。

## 脏标记追踪

`DirtyAwareModel` / `DirtyAwareBaseModel`（在 `amrita_core.dirty` 中）为 Pydantic 模型提供自动变更追踪。`MemoryModel` 继承自 `DirtyAwareBaseModel`，因此：

```python
memory = MemoryModel()
memory.messages.append(msg)     # 自动标记为脏
print(memory.is_dirty())        # True
print(memory.get_dirty_vars())  # {"messages"}
memory.clean()                  # 重置
```

这是为 ORM 风格的工作流设计的，只需持久化已更改的字段。
