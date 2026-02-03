import re
from functools import lru_cache
from typing import Literal

import jieba

jieba.initialize()


@lru_cache(maxsize=2048)
def hybrid_token_count(
    text: str,
    mode: Literal["word", "bpe", "char"] = "word",
    truncate_mode: Literal["head", "tail", "middle"] = "head",
) -> int:
    """
    Calculate token count for mixed Chinese-English text, supporting word, subword, and character modes

    Args:
        text: Input text
        mode: Tokenization mode ['char'(character-level), 'word'(word-level), 'bpe'(mixed mode)], default bpe
        truncate_mode: Truncation mode ['head'(head truncation), 'tail'(tail truncation), 'middle'(middle truncation)], default head

    Returns:
        int: Number of tokens
    """
    return Tokenizer(mode=mode, truncate_mode=truncate_mode).count_tokens(text=text)


class Tokenizer:
    """General purpose text tokenizer"""

    def __init__(
        self,
        max_tokens: int = 2048,
        mode: Literal["word", "bpe", "char"] = "bpe",
        truncate_mode: Literal["head", "tail", "middle"] = "head",
    ):
        """
        Initialize the tokenizer

        :param max_tokens: Maximum token limit, default 2048 (only effective in Word mode)
        :param mode: Tokenization mode ['char'(character-level), 'word'(word-level), 'bpe'(mixed mode)], default bpe
        :param truncate_mode: Truncation mode ['head'(head truncation), 'tail'(tail truncation), 'middle'(middle truncation)], default head
        """
        self.max_tokens = max_tokens
        self.mode = mode
        self.truncate_mode = truncate_mode
        self._word_pattern = re.compile(r"\w+|[^\w\s]")  # Match words or punctuation

    def tokenize(self, text: str) -> list[str]:
        """Perform tokenization operation, returning a list of tokens

        Args:
            text: Input text

        Returns:
            List[str]: List of tokens
        """
        if self.mode == "char":
            return list(text)

        # Mixed Chinese-English tokenization strategy
        tokens = []
        for chunk in re.findall(self._word_pattern, text):
            if chunk.strip() == "":
                continue

            if self._is_english(chunk):
                tokens.extend(chunk.split())
            else:
                tokens.extend(jieba.lcut(chunk))

        return tokens[: self.max_tokens] if self.mode == "word" else tokens

    def truncate(self, tokens: list[str]) -> list[str]:
        """Perform token truncation operation

        Args:
            tokens: List of tokens

        Returns:
            List[str]: Truncated list of tokens
        """
        if len(tokens) <= self.max_tokens:
            return tokens

        if self.truncate_mode == "head":
            return tokens[-self.max_tokens :]
        elif self.truncate_mode == "tail":
            return tokens[: self.max_tokens]
        else:  # middle mode preserves head and tail
            head_len = self.max_tokens // 2
            tail_len = self.max_tokens - head_len
            return tokens[:head_len] + tokens[-tail_len:]

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in text

        Args:
            text: Input text

        Returns:
            int: Number of tokens
        """
        return len(self.tokenize(text))

    def _is_english(self, text: str) -> bool:
        """Check if the text is English

        Args:
            text: Input text

        Returns:
            bool: Whether the text is English
        """
        return all(ord(c) < 128 for c in text)
