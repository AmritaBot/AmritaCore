from abc import ABC, abstractmethod
from typing import Literal

from amrita_sense.logging import logger

from amrita_core.threadsafe import ContextThreadsafe


class BaseTokenizer(ABC):
    __override__: bool = False  # Whether to allow overriding existing tokenizers

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if not getattr(cls, "__abstract__", False) and not getattr(
            cls, "__no_register__", False
        ):
            TokenizerManager().register_tokenizer(cls)

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

    @abstractmethod
    def tokenize(self, text: str) -> list[str]:
        """Perform tokenization operation, returning a list of tokens

        Args:
            text: Input text

        Returns:
            List[str]: List of tokens
        """
        ...

    @abstractmethod
    def truncate(self, tokens: list[str]) -> list[str]:
        """Perform token truncation operation

        Args:
            tokens: List of tokens

        Returns:
            List[str]: Truncated list of tokens
        """
        ...

    @staticmethod
    @abstractmethod
    def get_type() -> str:
        """Get the type of tokenizer, used for registration and retrieval"""
        ...


class TokenizerManager(ContextThreadsafe):
    __instance = None
    __inited = False
    _tokenizer_class: dict[str, type[BaseTokenizer]]

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance._tokenizer_class = {}
        return cls.__instance

    def __init__(self):
        if not self.__inited:
            super().__init__()
            self.__inited = True

    def get_tokenizers(self) -> dict[str, type[BaseTokenizer]]:
        """Get all registered tokenizers"""
        return self._tokenizer_class

    def safe_get_tokenizer(self, tok_type: str) -> type[BaseTokenizer] | None:
        """Get tokenizer"""
        return self._tokenizer_class.get(tok_type)

    def get_tokenizer(self, tok_type: str) -> type[BaseTokenizer]:
        """Get tokenizer"""
        if tok_type not in self._tokenizer_class:
            raise ValueError(f"No tokenizer found for tok_type {tok_type}")
        return self._tokenizer_class[tok_type]

    def register_tokenizer(self, tokenizer: type[BaseTokenizer]):
        """Register tokenizer"""
        tok_type = tokenizer.get_type()
        override = (
            tokenizer.__override__ if hasattr(tokenizer, "__override__") else False
        )
        if isinstance(tok_type, str):
            if tok_type in self._tokenizer_class:
                if not override:
                    raise ValueError(f"Tokenizer {tok_type} is already registered")
                logger.warning(
                    f"Tokenizer {tok_type} has been registered by {self._tokenizer_class[tok_type].__name__}, overriding existing tokenizer"
                )

            self._tokenizer_class[tok_type] = tokenizer
        else:
            raise TypeError("Type of tokenizer must be a string")
