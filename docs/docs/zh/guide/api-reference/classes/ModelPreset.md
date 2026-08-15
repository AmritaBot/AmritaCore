# ModelPreset

ModelPreset 类定义 AI 模型的预设配置。

## 属性

- `model` (str)：AI 模型的名称（如 gpt-3.5-turbo）
- `name` (str)：当前预设的标识符名称，默认为 "default"
- `base_url` (str)：API 服务的基础地址
- `api_key` (str)：访问 API 所需的密钥
- `protocol` (str)：协议适配器类型，默认为 `"__main__"`（OpenAI 兼容适配器）
- `config` ([ModelConfig](ModelConfig.md))：模型配置对象
- `thinking_config` ([ThinkingConfig](ThinkingConfig.md) | None)：思考/推理配置
- `rate` (float | None)：模型的 token 成本费率
- `extra` (dict[str, Any])：额外配置项

## 方法

- `load(path: Path)`：从指定路径加载模型预设配置
- `save(path: Path)`：将当前预设配置保存到指定路径
