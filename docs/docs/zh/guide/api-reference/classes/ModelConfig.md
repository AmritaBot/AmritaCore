# ModelConfig

ModelConfig 类定义 AI 模型的配置参数。

## 属性

- `top_k` (int)：默认值 50，控制模型考虑概率最高的 k 个词
- `top_p` (float)：默认值 0.95，控制模型考虑累积概率达到 p 的词
- `temperature` (float)：默认值 0.7，控制生成的随机性
- `stream` (bool)：默认值 False，是否启用流式响应
- `thought_chain_model` (bool)：默认值 False，是否启用思维链模型优化
- `multimodal` (bool)：默认值 False，是否支持多模态输入

## 描述

ModelConfig 类继承自 BaseModel，用于配置 AI 模型的行为参数。这些参数直接影响 AI 模型输出的质量和风格。
