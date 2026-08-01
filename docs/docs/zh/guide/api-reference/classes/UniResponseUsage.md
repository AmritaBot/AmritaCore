# UniResponseUsage

UniResponseUsage 类表示响应的使用统计信息。

## 属性

- `prompt_tokens` (T_INT)：提示词中使用的 token 数
- `completion_tokens` (T_INT)：完成（生成）中使用的 token 数
- `total_tokens` (T_INT)：使用的总 token 数
- `cache_creation` (int | None)：创建缓存条目使用的 token 数（Anthropic 提示缓存）
- `cache_hit` (int | None)：从缓存读取的 token 数（Anthropic 提示缓存）

## 描述

UniResponseUsage 类继承自 BaseModel 并实现泛型，用于记录和跟踪 AI 模型调用的使用信息。
