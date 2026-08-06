# 自定义 Tokenizer

Tokenizer 为用量统计与上下文管理计数 token。默认是轻量启发式；接入自己的
以获得供应商精确计数。

## 契约

`BaseTokenizer`（`amrita_core.base.tokenizer`）声明：

```python
from amrita_core.base.tokenizer import BaseTokenizer

class MyTokenizer(BaseTokenizer):
    def tokenize(self, text: str) -> list[str]:
        """把文本切成 token 列表。"""
        ...

    def truncate(self, tokens: list[str]) -> list[str]:
        """截断 token 列表（按模式 head/tail/middle）。"""
        ...

    @staticmethod
    def get_type() -> str:
        """注册键，如 "my-tokenizer"。"""
        return "my-tokenizer"
```

构造函数接受 `max_tokens`、`mode`（`"word"` / `"bpe"` / `"char"`）与
`truncate_mode`（`"head"` / `"tail"` / `"middle"`）。

## 自动注册

继承 `BaseTokenizer` **自动注册类**——`__init_subclass__` 调用
`TokenizerManager().register_tokenizer(cls)`，键来自 `get_type()`：

```python
from amrita_core.base.tokenizer import BaseTokenizer

class MyTokenizer(BaseTokenizer):
    ...

# 完成——`TokenizerManager().get_tokenizer("my-tokenizer")` 现在能找到它。
```

在类上设 `__override__ = True` 可替换同类型已注册的 tokenizer。

## 为什么重要

- **用量统计**：`UniResponseUsage` 与 `TokenBudget`（step 循环的压缩触发）
  来自 token 计数
- **记忆摘要**：`memory_abstract_threshold` 用你的 tokenizer 计数比较
  prompt tokens
- **上下文上限**：精确计数让请求保持在窗口内

> 对大多数供应商启发式默认足够；依赖精确阈值时使用供应商精确 tokenizer
> （如 OpenAI 模型用 `tiktoken`）。

## 下一步

[代理工程](../agent-engineering/index.md)——调优提示词、模板并排查常见问题。
