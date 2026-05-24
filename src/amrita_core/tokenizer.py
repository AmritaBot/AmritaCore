from functools import lru_cache
from typing import Literal

from amrita_core.base.tokenizer import TokenizerManager


@lru_cache(maxsize=2048)
def hybrid_token_count(
    text: str,
    mode: Literal["word", "bpe", "char"] = "word",
    truncate_mode: Literal["head", "tail", "middle"] = "head",
    tokenizer_type: str = "simple",
) -> int:
    """
    Calculate token count for mixed Chinese-English text, supporting word, subword, and character modes (This is just a simple implementation, and you can use other tokenization methods if you need more accurate results)

    Args:
        text: Input text
        mode: Tokenization mode ['char'(character-level), 'word'(word-level), 'bpe'(mixed mode)], default bpe
        truncate_mode: Truncation mode ['head'(head truncation), 'tail'(tail truncation), 'middle'(middle truncation)], default head
        tokenizer_type: The type of tokenizer to use for estimation, default "simple". This should correspond to a registered tokenizer type in the TokenizerManager.

    Returns:
        int: Number of tokens
    """
    return len(
        TokenizerManager()
        .get_tokenizer(tokenizer_type)(mode=mode, truncate_mode=truncate_mode)
        .tokenize(
            text,
        )
    )
