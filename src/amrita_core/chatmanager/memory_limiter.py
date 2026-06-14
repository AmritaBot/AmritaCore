import asyncio
import copy
from types import TracebackType

from typing_extensions import Self

from amrita_core.config import AmritaConfig, get_config
from amrita_core.consts import ABSTRACT_INSTRUCTION
from amrita_core.libchat import (
    call_completion,
    get_last_response,
    get_tokens,
    text_generator,
)
from amrita_core.logging import logger
from amrita_core.tokenizer import hybrid_token_count
from amrita_core.types import (
    CONTENT_LIST_TYPE,
    CT_MAP,
    Content,
    Message,
    ToolResult,
    UniResponseUsage,
)
from amrita_core.types import (
    MemoryModel as Memory,
)


class MemoryLimiter:
    """Context processor

    This class is responsible for handling context memory length and token count limits,
    ensuring the chat context remains within predefined constraints by summarizing
    context and removing messages to avoid exceeding the model processing capacity.
    """

    config: AmritaConfig  # Configuration object
    usage: UniResponseUsage | None = None  # Token usage, initially None
    _train: Message[str]  # Training data (system prompts)
    _dropped_messages: list[Message[str] | ToolResult]  # List of removed messages
    _copied_messages: Memory  # Original message copies (for rollback on exceptions)
    _abstract_instruction = ABSTRACT_INSTRUCTION

    def __init__(
        self,
        memory: Memory,
        train: dict[str, str] | Message[str],
        config: AmritaConfig | None = None,
        abstract_instruction: str | None = None,
    ) -> None:
        """Initialize context processor

        Args:
            memory: Memory model to process
            train: Training data (system prompts)
        """
        self.memory: Memory = memory
        self.config = config or get_config()
        self._train = (
            train if isinstance(train, Message) else Message[str].model_validate(train)
        )
        self._abstract_instruction = abstract_instruction or ABSTRACT_INSTRUCTION

    async def __aenter__(self) -> Self:
        """Async context manager entry, initialize processing state

        Returns:
            Return instance for use
        """
        self._dropped_messages = []
        self._copied_messages = copy.deepcopy(self.memory)
        logger.debug(
            f"MemoryLimiter initialized, message count: {len(self.memory.messages)}"
        )
        return self

    @classmethod
    def set_abstract_instruction(cls, instruction: str):
        """Set abstract instruction

        Args:
            instruction: Abstract instruction
        """
        if not isinstance(instruction, str):
            raise TypeError("Instruction must be a string")
        elif not instruction:
            raise ValueError("Instruction cannot be empty")
        cls._abstract_instruction = instruction

    @classmethod
    def get_abstract_instruction(cls) -> str:
        """Get abstract instruction

        Returns:
            Abstract instruction
        """
        return cls._abstract_instruction

    @classmethod
    def reset_abstract_instruction(cls):
        """Reset abstract instruction"""
        cls._abstract_instruction = ABSTRACT_INSTRUCTION

    async def _make_abstract(self):
        """Generate context summary

        By calling LLM to summarize all message content in the current memory into a brief content,
        to reduce context length while preserving key information.
        """
        logger.debug("Starting context summarization..")
        proportion = self.config.llm.memory_abstract_proportion  # Summary proportion
        dropped_part: CONTENT_LIST_TYPE = copy.deepcopy(self._dropped_messages)
        index = int(len(self.memory.messages) * proportion) - len(dropped_part)
        if index < 0:
            index = 0
        if index:
            idx = 0
            while idx < len(self.memory.messages):
                element = self.memory.messages[idx]
                dropped_part.append(element)
                if getattr(element, "tool_calls", None) is not None:
                    # This is an assistant message that initiated tool calls
                    # Include all subsequent consecutive tool messages
                    next_idx = idx + 1
                    while next_idx < len(self.memory.messages):
                        next_element = self.memory.messages[next_idx]
                        # Check if this is a tool message (role == 'tool')
                        if getattr(next_element, "role", None) == "tool":
                            dropped_part.append(next_element)
                            next_idx += 1
                        else:
                            break
                    # Update idx to the position after the last processed tool message
                    idx = next_idx
                else:
                    idx += 1
                if idx >= index:
                    break
            self.memory.messages = self.memory.messages[idx:]
        if dropped_part:
            msg_list: CONTENT_LIST_TYPE = [
                Message[str](role="system", content=self._abstract_instruction),
                Message[str](
                    role="user",
                    content=(
                        "Make a summary of full informations in message list:\n\n```text\n".join(
                            [
                                f"{it}\n"
                                for it in text_generator(
                                    dropped_part,
                                    split_role=True,
                                )
                            ]
                        )
                        + "\n```"
                    ),
                ),
            ]
            logger.debug("Performing context summarization...")
            response = await get_last_response(call_completion(msg_list))
            usage = get_tokens(
                msg_list, response
            )  # Well, this is just a rough calculation.
            self.usage = usage
            logger.debug(f"Context summary received: {response.content}")
            self.memory.abstract = response.content
            logger.debug("Context summarization completed")
        else:
            logger.debug("Context summarization skipped")

    def _drop_message(self):
        """Remove the oldest message from memory and add it to dropped messages list.

        This method removes the first message from the memory and adds it to the
        dropped messages list. If the next message is a tool message, it is also
        removed and added to the dropped messages list.
        """
        data = self.memory
        if len(data.messages) <= 1:
            return
        self._dropped_messages.append(data.messages.pop(0))
        if data.messages[0].role == "tool":
            while data.messages and data.messages[0].role == "tool":
                self._dropped_messages.append(data.messages.pop(0))

    async def run_enforce(self):
        """Execute memory limitation processing

        Execute memory length limitation and token count limitation in sequence,
        ensuring the chat context stays within predefined ranges.
        This method must be used within an async context manager.

        Raises:
            RuntimeError: Thrown when not used in an async context manager
        """
        logger.debug("Starting memory limitation processing..")
        if not hasattr(self, "_dropped_messages") and not hasattr(
            self, "_copied_messages"
        ):
            raise RuntimeError(
                "MemoryLimiter is not initialized, please use `async with MemoryLimiter(memory)` before calling."
            )
        await self._limit_length()
        await self._limit_tokens()
        if self.config.llm.enable_memory_abstract and self._dropped_messages:
            await self._make_abstract()
        logger.debug("Memory limitation processing completed")

    async def _limit_length(self):
        """Control memory length, remove old messages that exceed the limit, remove unsupported messages."""
        logger.debug("Starting memory length limitation..")
        is_multimodal = self.config.llm.enable_multi_modal
        data: Memory = self.memory

        # Process multimodal messages when needed
        for message in data.messages:
            if (
                isinstance(message.content, list)
                and not is_multimodal
                and message.role == "user"
            ):
                message_text = ""
                for content_part in message.content:
                    if isinstance(content_part, dict):
                        validator = CT_MAP.get(content_part["type"])
                        if not validator:
                            raise ValueError(
                                f"Invalid content type: {content_part['type']}"
                            )
                        content_part: Content = validator.model_validate(content_part)
                    if content_part["type"] == "text":
                        message_text += content_part["text"]
                message.content = message_text

        # Enforce memory length limit
        initial_count = len(data.messages)
        while len(data.messages) > 1:
            if data.messages[0].role == "tool":
                data.messages.pop(0)
            elif len(data.messages) > self.config.llm.memory_length_limit:
                self._drop_message()
            else:
                break
        final_count = len(data.messages)
        logger.debug(
            f"Memory length limitation completed, removed {initial_count - final_count} messages"
        )

    async def _limit_tokens(self):
        """Control token count, remove old messages that exceed the limit

        Calculate the token count of the current message list, when exceeding the configured session max token limit,
        gradually remove the earliest messages until satisfying the token count limit.
        """

        def get_token(memory: CONTENT_LIST_TYPE) -> int:
            """Calculate the total token count for a given message list

            Args:
                memory: List of messages to calculate token count for

            Returns:
                Total token count for the messages
            """
            tk_tmp: int = 0
            for msg in text_generator(memory, full_message=True):
                tk_tmp += hybrid_token_count(
                    msg,
                    self.config.llm.tokens_count_mode,
                    tokenizer_type=self.config.function_config.tokenizer_used,
                )
            return tk_tmp

        train = self._train
        train_model = Message.model_validate(train)
        data = self.memory
        logger.debug("Starting token count limitation..")
        memory_l: CONTENT_LIST_TYPE = [train_model, *data.messages]
        if not self.config.llm.enable_tokens_limit:
            logger.debug("Token limitation disabled, skipping processing")
            return
        prompt_length = hybrid_token_count(
            train.content,
            self.config.llm.tokens_count_mode,
            tokenizer_type=self.config.function_config.tokenizer_used,
        )
        if prompt_length > self.config.llm.session_tokens_windows:
            logger.warning(
                f"Prompt size too large! It's {prompt_length}>{self.config.llm.session_tokens_windows}! Please adjusts the prompt or settings!"
            )
            return
        tk_tmp: int = get_token(memory_l)

        initial_count = len(data.messages)
        while tk_tmp > self.config.llm.session_tokens_windows:
            if len(data.messages) > 1:
                self._drop_message()
            else:
                break

            tk_tmp: int = get_token(memory_l)
            memory_l = [train_model, *data.messages]
            await asyncio.sleep(
                0
            )  # CPU intensive tasks may cause performance issues, yielding control here
        final_count = len(data.messages)
        logger.debug(
            f"Token count limitation completed, removed {initial_count - final_count} messages"
        )
        logger.debug(f"Final token count: {tk_tmp}")

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit, handle rollback in case of exceptions

        In case of exceptions, restore messages to the state before processing,
        ensuring data consistency.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        del exc_val, exc_tb
        if exc_type is not None:
            logger.warning("An exception occurred, rolling back messages...")
            self.memory.messages = self._copied_messages.messages
            return
