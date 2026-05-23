import re
from typing import Literal

from amrita_core.base.tokenizer import BaseTokenizer


class SimpleTokenizer(BaseTokenizer):
    """A simple regex-based tokenizer for token estimation.

    This tokenizer splits text on whitespace and punctuation while preserving
    the punctuation characters as separate tokens. Markdown formatting symbols
    (such as **, *, ```) are also split out and preserved. Long continuous
    word-like tokens (longer than 4 characters) are further chunked into 4‑char
    pieces to roughly mimic subword tokenization. It is intended for rough
    token counting only and does NOT produce linguistically accurate tokens.
    """

    __override__ = False

    def __init__(
        self,
        max_tokens: int = 2048,
        mode: Literal["word", "bpe", "char"] = "bpe",
        truncate_mode: Literal["head", "tail", "middle"] = "head",
    ):
        super().__init__(
            max_tokens=max_tokens,
            mode=mode,
            truncate_mode=truncate_mode,
        )
        self._token_pattern = re.compile(
            r"\*\*|\*|```|``|`|[^\w\s]|\w+|[\u4e00-\u9fff]"
        )

    @staticmethod
    def get_type() -> str:
        return "simple"

    def tokenize(self, text: str) -> list[str]:
        """Split text into tokens suitable for length estimation.

        Args:
            text: The input text.

        Returns:
            A list of token strings.
        """
        raw_matches = self._token_pattern.findall(text)
        tokens: list[str] = []
        for match in raw_matches:
            # If the match consists solely of word characters or Chinese
            # characters and is longer than 4, split it into 4‑char chunks.
            if re.fullmatch(r"\w+|[\u4e00-\u9fff]+", match) and len(match) > 4:
                tokens.extend([match[i : i + 4] for i in range(0, len(match), 4)])
            else:
                tokens.append(match)
        return tokens

    def truncate(self, tokens: list[str]) -> list[str]:
        """Truncate token list according to max_tokens and truncate_mode.

        Args:
            tokens: The token list to truncate.

        Returns:
            A truncated token list.
        """
        if len(tokens) <= self.max_tokens:
            return tokens

        if self.truncate_mode == "head":
            return tokens[-self.max_tokens :]
        elif self.truncate_mode == "tail":
            return tokens[: self.max_tokens]
        else:  # middle mode preserves both head and tail
            head_len = self.max_tokens // 2
            tail_len = self.max_tokens - head_len
            return tokens[:head_len] + tokens[-tail_len:]
