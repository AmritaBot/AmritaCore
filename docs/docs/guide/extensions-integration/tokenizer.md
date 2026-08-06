# Custom Tokenizers

Tokenizers count tokens for usage accounting and context management. The
default is a lightweight heuristic; plug your own for provider-exact counts.

## The Contract

`BaseTokenizer` (in `amrita_core.base.tokenizer`) declares:

```python
from amrita_core.base.tokenizer import BaseTokenizer

class MyTokenizer(BaseTokenizer):
    def tokenize(self, text: str) -> list[str]:
        """Split text into tokens."""
        ...

    def truncate(self, tokens: list[str]) -> list[str]:
        """Truncate a token list (head/tail/middle per mode)."""
        ...

    @staticmethod
    def get_type() -> str:
        """Registration key, e.g. "my-tokenizer"."""
        return "my-tokenizer"
```

The constructor accepts `max_tokens`, `mode` (`"word"` / `"bpe"` / `"char"`)
and `truncate_mode` (`"head"` / `"tail"` / `"middle"`).

## Registration Is Automatic

Subclassing `BaseTokenizer` **registers the class automatically** —
`__init_subclass__` calls `TokenizerManager().register_tokenizer(cls)` with
the key from `get_type()`:

```python
from amrita_core.base.tokenizer import BaseTokenizer

class MyTokenizer(BaseTokenizer):
    ...

# Done — `TokenizerManager().get_tokenizer("my-tokenizer")` now finds it.
```

Set `__override__ = True` on the class to replace an existing tokenizer with
the same type.

## Why It Matters

- **Usage accounting**: `UniResponseUsage` values and `TokenBudget` (the step
  loop's compression trigger) derive from token counts
- **Memory summarization**: `memory_abstract_threshold` compares prompt tokens
  against your tokenizer's count
- **Context limits**: accurate counts keep requests inside the window

> Heuristic default is fine for most providers; use a provider-exact tokenizer
> (e.g. `tiktoken` for OpenAI models) when you depend on precise thresholds.

## Next

[Agent Engineering](../agent-engineering/index.md) — tune prompts, templates
and troubleshoot common problems.
