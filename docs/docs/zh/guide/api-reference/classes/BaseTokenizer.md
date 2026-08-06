# BaseTokenizer

BaseTokenizer 类是分词器的抽象基类。

## 描述

BaseTokenizer（继承 `ABC`）定义了分词器接口。子类通过 `__init_subclass__` 自动注册到 `TokenizerManager` 中（除非标记为 `__abstract__` 或 `__no_register__`），每个子类必须实现 `tokenize`、`truncate` 和静态方法 `get_type`。

## 构造函数参数

- `max_tokens` (int)：默认 `2048`。最大 token 限制（仅在 word 模式下生效）
- `mode` (Literal["word", "bpe", "char"])：默认 `"bpe"`。分词模式：char（字符级）、word（词级）、bpe（混合）
- `truncate_mode` (Literal["head", "tail", "middle"])：默认 `"head"`。截断模式

## 抽象方法

- `tokenize(text: str) -> list[str]`：执行分词，返回 token 列表
- `truncate(tokens: list[str]) -> list[str]`：执行 token 截断
- `static get_type() -> str`：获取分词器类型，用于注册和检索

## 示例

```python
from amrita_core.base.tokenizer import BaseTokenizer


class MyTokenizer(BaseTokenizer):
    @staticmethod
    def get_type() -> str:
        return "my_tokenizer"

    def tokenize(self, text: str) -> list[str]:
        return list(text)

    def truncate(self, tokens: list[str]) -> list[str]:
        return tokens[: self.max_tokens]
```
