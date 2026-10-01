# ModelPreset

ModelPreset 类定义 AI 模型的预设配置。

## 属性

- `model` (str)：AI 模型的名称（如 gpt-3.5-turbo）
- `name` (str)：当前预设的标识符名称，默认为 "default"
- `base_url` (str)：API 服务的基础地址
- `api_key` (str)：访问 API 所需的密钥
- `protocol` (str)：协议适配器类型，默认为 `"__main__"`（OpenAI 兼容适配器）
- `rate` ([RateConfig](RateConfig.md) | None)：用于成本核算的价格快照。在该预设生效期间，会逐字复制进每一条 [BillingRecord](BillingRecord.md)
- `max_context` (int | None)：模型的输入 token 预算。与 `max_output` 共同构成注意力窗口。未设置时回退到 `LLMConfig.session_tokens_windows`
- `max_output` (int | None)：为响应预留的 token 数。未设置时回退到 `LLMConfig.max_tokens`
- `config` (`ModelConfig`)：模型配置对象
- `thinking_config` ([ThinkingConfig](ThinkingConfig.md) | None)：思考/推理配置
- `extra` (dict[str, Any])：额外配置项

## 方法

- `load(path: Path)`：从指定路径加载模型预设配置
- `save(path: Path)`：将当前预设配置保存到指定路径

## 解析窗口值

两个模块级辅助函数负责把预设字段与全局配置合成一个确定值，调用方无需自行判断 `None`：

```python
from amrita_core.types.preset import resolve_max_context, resolve_max_output

window = resolve_max_context(preset, config)  # preset.max_context 或 config.llm.session_tokens_windows
budget = resolve_max_output(preset, config)  # preset.max_output 或 config.llm.max_tokens
```

模型适配器用 `resolve_max_output` 生成请求的 `max_tokens` 参数，`ContextCompactor` 用 `resolve_max_context` 计算压缩阈值。

> 由于 `rate.input` / `rate.output` 是 `Decimal`，`model_dump()` 返回的是 `Decimal` 对象。`save()` 因此写出 `model_dump(mode="json")`；你自己的序列化代码也应如此。
