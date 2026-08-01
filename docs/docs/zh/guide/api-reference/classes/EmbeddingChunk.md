# EmbeddingChunk

`EmbeddingChunk` 表示嵌入适配器返回的嵌入向量。

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
- **描述**：输入序列中对应文本的原始索引。

## 使用示例

```python
from amrita_core.types import EmbeddingChunk

chunk = EmbeddingChunk(
    embedding=[0.1, -0.5, 0.8, 0.3],
    index=0
)

texts = ["你好", "世界"]
embeddings: list[EmbeddingChunk] = await call_completion(preset=embedding_preset, messages=texts)
```
