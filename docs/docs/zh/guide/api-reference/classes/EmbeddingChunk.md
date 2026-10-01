# EmbeddingChunk

`EmbeddingChunk` 表示嵌入适配器返回的嵌入向量。

## 概述

`EmbeddingChunk` 类表示嵌入适配器返回的单个嵌入向量。它为嵌入结果提供标准化结构，
在保持与 OpenAI 嵌入响应格式兼容的同时增加了类型安全。

## 类定义

```python
class EmbeddingChunk(BaseModel):
    embedding: Sequence[float]
    index: int
```

## 属性

### `embedding`

- **类型**：`Sequence[float]`
- **描述**：嵌入向量，作为浮点数的序列。表示输入文本在向量空间中的语义表示。

### `index`

- **类型**：`int`
- **描述**：输入序列中对应文本的原始索引。处理多个输入时，可据此把嵌入映射回源
  文本。

## 使用示例

```python
from amrita_core.types import EmbeddingChunk

# 创建一个嵌入块
chunk = EmbeddingChunk(embedding=[0.1, -0.5, 0.8, 0.3], index=0)

print(f"Vector: {chunk.embedding}")
print(f"Original index: {chunk.index}")

# 处理多个文本时
texts = ["你好", "世界"]
embeddings: list[EmbeddingChunk] = await call_completion(
    preset=embedding_preset, messages=texts
)

for chunk in embeddings:
    print(f"Text '{texts[chunk.index]}' -> Embedding length: {len(chunk.embedding)}")
```

## 相关组件

- [`ModelAdapter.call_embed()`](ModelAdapter.md#call_embed)：返回 `EmbeddingChunk` 实例的方法
- [`ModelAdapter`](ModelAdapter.md)：适配器基类，使用 `ADAPTER_TYPE` 字面量类型
- `call_completion()`：处理嵌入适配器调用的函数
