# BaseTokenizer

The BaseTokenizer class is the abstract base class for tokenizers.

## Description

BaseTokenizer (inheriting from `ABC`) defines the tokenizer interface. Subclasses are automatically registered into the `TokenizerManager` via `__init_subclass__` (unless marked `__abstract__` or `__no_register__`), and each must implement `tokenize`, `truncate`, and the static `get_type`.

## Constructor Parameters

- `max_tokens` (int): Default `2048`. Maximum token limit (only effective in word mode)
- `mode` (Literal["word", "bpe", "char"]): Default `"bpe"`. Tokenization mode: char (character-level), word (word-level), bpe (mixed)
- `truncate_mode` (Literal["head", "tail", "middle"]): Default `"head"`. Truncation mode

## Abstract Methods

- `tokenize(text: str) -> list[str]`: Perform tokenization, returning a list of tokens
- `truncate(tokens: list[str]) -> list[str]`: Perform token truncation
- `static get_type() -> str`: Get the type of tokenizer, used for registration and retrieval

## Example

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
