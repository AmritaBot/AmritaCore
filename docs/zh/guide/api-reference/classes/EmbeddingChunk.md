# EmbeddingChunk

`EmbeddingChunk` 表示嵌入适配器返回的嵌入向量。

## 概述

`EmbeddingChunk` 类表示嵌入适配器返回的单个嵌入向量。它为嵌入结果提供了标准化结构，在保持与OpenAI嵌入响应格式兼容的同时增加了类型安全性。

## 类定义

```python
class EmbeddingChunk(BaseModel):
    embedding: Sequence[float]
    index: int
```

## 属性

### `embedding`

- **类型**: `Sequence[float]`
- **描述**: 作为浮点数序列的嵌入向量。这表示输入文本在向量空间中的语义表示。

### `index`

- **类型**: `int`
- **描述**: 对应文本在输入序列中的原始索引。这允许在处理多个输入时将嵌入映射回其源文本。

## 使用示例

```python
from amrita_core.types import EmbeddingChunk

# 创建嵌入块
chunk = EmbeddingChunk(
    embedding=[0.1, -0.5, 0.8, 0.3],
    index=0
)

print(f"向量: {chunk.embedding}")
print(f"原始索引: {chunk.index}")

# 处理多个文本时
texts = ["Hello", "World"]
embeddings: list[EmbeddingChunk] = await call_completion(preset=embedding_preset, messages=texts)

for chunk in embeddings:
    print(f"文本 '{texts[chunk.index]}' -> 嵌入长度: {len(chunk.embedding)}")
```

## 相关组件

- [`ModelAdapter.call_embed()`](ModelAdapter.md#call_embed): 返回 `EmbeddingChunk` 实例的方法
- [`ADAPTER_TYPE`](ADAPTER_TYPE.md): 包含 `"embed"` 类型的枚举
- [`call_completion()`](../functions/call_completion.md): 处理嵌入适配器调用的函数
