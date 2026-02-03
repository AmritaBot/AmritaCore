import asyncio
import copy
from abc import ABC
from asyncio import Lock, Task
from collections import defaultdict
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from typing import Any
from uuid import uuid4

import pytz
from pydantic import BaseModel, Field
from pytz import utc
from typing_extensions import Self

from .config import AmritaConfig, get_config
from .hook.event import CompletionEvent, PreCompletionEvent
from .hook.matcher import MatcherManager
from .libchat import call_completion, get_last_response, get_tokens, text_generator
from .logging import debug_log
from .tokenizer import hybrid_token_count
from .types import (
    CONTENT_LIST_TYPE,
    CT_MAP,
    USER_INPUT,
    Content,
    ImageContent,
    Message,
    TextContent,
    ToolResult,
    UniResponse,
    UniResponseUsage,
)
from .types import (
    MemoryModel as Memory,
)

# Global lock for thread-safe operations in the chat manager
LOCK = Lock()


def get_current_datetime_timestamp(utc_time: None | datetime = None):
    """Get current time and format as date, weekday and time string in Asia/Shanghai timezone

    Args:
        utc_time: Optional datetime object in UTC. If None, current time will be used

    Returns:
        Formatted timestamp string in the format "[YYYY-MM-DD Weekday HH:MM:SS]"
    """
    utc_time = utc_time or datetime.now(pytz.utc)
    asia_shanghai = pytz.timezone("Asia/Shanghai")
    now = utc_time.astimezone(asia_shanghai)
    formatted_date = now.strftime("%Y-%m-%d")
    formatted_weekday = now.strftime("%A")
    formatted_time = now.strftime("%H:%M:%S")
    return f"[{formatted_date} {formatted_weekday} {formatted_time}]"


class MessageContent(ABC):
    """Abstract base class for different types of message content

    This allows for various types of content to be yielded by the chat manager,
    not just strings. Subclasses should implement their own representation.
    """

    def __init__(self, content_type: str):
        self.type = content_type

    def get_content(self):
        """Return the actual content of the message"""
        raise NotImplementedError("Subclasses must implement get_content method")


class StringMessageContent(MessageContent):
    """String type message content implementation"""

    def __init__(self, text: str):
        super().__init__("string")
        self.text = text

    def get_content(self):
        return self.text


class RawMessageContent(MessageContent):
    """Raw message content implementation"""

    def __init__(self, raw_data: Any):
        super().__init__("raw")
        self.raw_data = raw_data

    def get_content(self):
        return self.raw_data


class MessageWithMetadata(MessageContent):
    """Message with additional metadata"""

    def __init__(self, content: Any, metadata: dict):
        super().__init__("metadata")
        self.content = content
        self.metadata = metadata

    def get_content(self):
        return {"content": self.content, "metadata": self.metadata}


class ChatObjectMeta(BaseModel):
    """Metadata model for chat object

    Used to store identification, events, and time information for the chat object.
    """

    stream_id: str  # Chat stream ID
    session_id: str  # Session ID
    user_query: list[TextContent | ImageContent] | str
    time: datetime = Field(default_factory=datetime.now)  # Creation time
    last_call: datetime = Field(default_factory=datetime.now)  # Last call time


class MemoryLimiter:
    """Context processor

    This class is responsible for handling context memory length and token count limits,
    ensuring the chat context remains within predefined constraints by summarizing
    context and removing messages to avoid exceeding the model processing capacity.
    """

    config: AmritaConfig  # Configuration object
    usage: UniResponseUsage | None = None  # Token usage, initially None
    _train: dict[str, str]  # Training data (system prompts)
    _dropped_messages: list[Message[str] | ToolResult]  # List of removed messages
    _copied_messages: Memory  # Original message copies (for rollback on exceptions)
    _abstract_instruction = """<<SYS>>
You are a professional context summarizer, strictly following user instructions to perform summarization tasks.
<</SYS>>

<<INSTRUCTIONS>>
1. Directly summarize the user-provided content
2. Maintain core information and key details from the original
3. Do not generate any additional content, explanations, or comments
4. Summaries should be concise, accurate, complete
<</INSTRUCTIONS>>

<<RULE>>
- Only summarize the text provided by the user
- Do not add any explanations, comments, or supplementary information
- Do not alter the main meaning of the original
- Maintain an objective and neutral tone
<</RULE>>

<<FORMATTING>>
User input → Direct summary output
<</FORMATTING>>"""

    def __init__(self, memory: Memory, train: dict[str, str]) -> None:
        """Initialize context processor

        Args:
            memory: Memory model to process
            train: Training data (system prompts)
        """
        self.memory = memory
        self.config = get_config()
        self._train = train

    async def __aenter__(self) -> Self:
        """Async context manager entry, initialize processing state

        Returns:
            Return instance for use
        """
        self._dropped_messages = []
        self._copied_messages = copy.deepcopy(self.memory)
        debug_log(
            f"MemoryLimiter initialized, message count: {len(self.memory.messages)}"
        )
        return self

    async def _make_abstract(self):
        """Generate context summary

        By calling LLM to summarize all message content in the current memory into a brief content,
        to reduce context length while preserving key information.
        """
        debug_log("Starting context summarization..")
        proportion = self.config.llm.memory_abstract_proportion  # Summary proportion
        dropped_part: CONTENT_LIST_TYPE = copy.deepcopy(self._dropped_messages)
        index = int(len(self.memory.messages) * proportion) - len(dropped_part)
        if index < 0:
            index = 0
        idx: int | None = None
        if index:
            for idx, element in enumerate(self.memory.messages):
                dropped_part.append(element)
                if (
                    getattr(element, "tool_calls", None) is not None
                ):  # Remove along with tool calls (system(tool_call),tool_call)
                    continue
                elif idx >= index:
                    break
        self.memory.messages = self.memory.messages[
            (idx if idx is not None else index) :  # Remove some messages
        ]
        if dropped_part:
            msg_list: CONTENT_LIST_TYPE = [
                Message[str](role="system", content=self._abstract_instruction),
                Message[str](
                    role="user",
                    content=(
                        "Message list:\n```text\n".join(
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
            debug_log("Performing context summarization...")
            response = await get_last_response(call_completion(msg_list))
            usage = await get_tokens(msg_list, response)
            self.usage = usage
            debug_log(f"Context summary received: {response.content}")
            self.memory.abstract = response.content
            debug_log("Context summarization completed")
        else:
            debug_log("Context summarization skipped")

    def _drop_message(self):
        """Remove the oldest message from memory and add it to dropped messages list.

        This method removes the first message from the memory and adds it to the
        dropped messages list. If the next message is a tool message, it is also
        removed and added to the dropped messages list.
        """
        data = self.memory
        if len(data.messages) < 2:
            return
        self._dropped_messages.append(data.messages.pop(0))
        if data.messages[0].role == "tool":
            self._dropped_messages.append(data.messages.pop(0))

    async def run_enforce(self):
        """Execute memory limitation processing

        Execute memory length limitation and token count limitation in sequence,
        ensuring the chat context stays within predefined ranges.
        This method must be used within an async context manager.

        Raises:
            RuntimeError: Thrown when not used in an async context manager
        """
        debug_log("Starting memory limitation processing..")
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
        debug_log("Memory limitation processing completed")

    async def _limit_length(self):
        """Control memory length, remove old messages that exceed the limit, remove unsupported messages."""
        debug_log("Starting memory length limitation..")
        is_multimodal = get_config().llm.enable_multi_modal
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
        while len(data.messages) >= 2:
            if data.messages[0].role == "tool":
                data.messages.pop(0)
            elif len(data.messages) > self.config.llm.memory_lenth_limit:
                self._drop_message()
            else:
                break
        final_count = len(data.messages)
        debug_log(
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
            for msg in text_generator(memory):
                tk_tmp += hybrid_token_count(
                    msg,
                    self.config.llm.tokens_count_mode,
                )
            return tk_tmp

        train = self._train
        train_model = Message.model_validate(train)
        data = self.memory
        debug_log("Starting token count limitation..")
        memory_l: CONTENT_LIST_TYPE = [train_model, *data.messages]
        if not self.config.llm.enable_tokens_limit:
            debug_log("Token limitation disabled, skipping processing")
            return
        prompt_length = hybrid_token_count(train["content"])
        if prompt_length > self.config.llm.session_tokens_windows:
            print(
                f"Prompt size too large! It's {prompt_length}>{self.config.llm.session_tokens_windows}! Please adjusts the prompt or settings!"
            )
            return
        tk_tmp: int = get_token(memory_l)

        initial_count = len(data.messages)
        while tk_tmp > self.config.llm.session_tokens_windows:
            if len(data.messages) >= 2:
                self._drop_message()
            else:
                break

            tk_tmp: int = get_token(memory_l)
            memory_l = [train_model, *data.messages]
            await asyncio.sleep(
                0
            )  # CPU intensive tasks may cause performance issues, yielding control here
        final_count = len(data.messages)
        debug_log(
            f"Token count limitation completed, removed {initial_count - final_count} messages"
        )
        debug_log(f"Final token count: {tk_tmp}")

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit, handle rollback in case of exceptions

        In case of exceptions, restore messages to the state before processing,
        ensuring data consistency.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if exc_type is not None:
            print("An exception occurred, rolling back messages...")
            self.memory.messages = self._copied_messages.messages
            return


class ChatObject:
    """Chat processing object

    This class is responsible for processing a single chat session, including message receiving,
    context management, model calling, and response sending.
    """

    stream_id: str  # Chat object ID
    timestamp: str  # Timestamp (for LLM)
    time: datetime  # Time
    end_at: datetime | None = None
    data: Memory  # (lateinit) Memory file
    user_input: USER_INPUT
    train: dict[str, str]  # System message
    last_call: datetime  # Last internal function call time
    session_id: str
    response: UniResponse[str, None]
    _is_running: bool = False  # Whether it is running
    _is_done: bool = False  # Whether it has completed
    _task: Task[None]
    _has_task: bool = False
    _err: BaseException | None = None
    _wait: bool = True
    _queue_done: bool = False

    def __init__(
        self,
        train: dict[str, str],
        user_input: USER_INPUT,
        context: Memory,
        session_id: str,
        run_blocking: bool = True,
    ) -> None:
        """Initialize chat object

        Args:
            train: Training data (system prompts)
            user_input: Input from the user
            context: Memory context for the session
            session_id: Unique identifier for the session
            run_blocking: Whether to run in blocking mode
        """
        self.train = train
        self.data = context
        self.session_id = session_id
        self.user_input = user_input
        self.timestamp = get_current_datetime_timestamp()
        self.time = datetime.now(utc)
        self.config: AmritaConfig = get_config()
        self.last_call = datetime.now(utc)
        self._wait = run_blocking

        # Initialize async queue for streaming responses
        self.response_queue = asyncio.Queue(25)
        self.__done_marker = object()  # Special marker to signal completion

    def get_exception(self) -> BaseException | None:
        """
        Get exceptions that occurred during task execution

        Returns:
            BaseException | None: Returns exception object if an exception occurred during task execution, otherwise returns None
        """
        return self._err

    def call(self):
        """
        Get callable object

        Returns:
            Callable object (usually the class's __call__ method)
        """
        return self.__call__()

    def is_running(self) -> bool:
        """
        Check if the task is running

        Returns:
            bool: Returns True if the task is running, otherwise returns False
        """
        return self._is_running

    def is_done(self) -> bool:
        """
        Check if the task has completed

        Returns:
            bool: Returns True if the task has completed, otherwise returns False
        """
        return self._is_done

    def terminate(self) -> None:
        """
        Terminate task execution
        Sets the task status to completed and cancels the internal task
        """
        self._is_done = True
        self._is_running = False
        self._task.cancel()

    def __await__(self):
        if not hasattr(self, "_task"):
            raise RuntimeError("ChatObject not running")
        return self._task.__await__()

    async def __call__(self) -> None:
        """Call chat object to process messages

        Args:
            event: Message event
            matcher: Matcher
            bot: Bot instance
        """
        if not self._has_task:
            debug_log("Starting chat object task...")
            self._has_task = True
            self._task = asyncio.create_task(self.__call__())
            return await self._task if self._wait else None
        if not self._is_running and not self._is_done:
            debug_log(f"Starting chat processing, stream ID:{self.stream_id}")
            self.stream_id = uuid4().hex

            try:
                self._is_running = True
                self.last_call = datetime.now(utc)
                await chat_manager.add_chat_object(self)

                await self._run()
            finally:
                self._is_running = False
                self._is_done = True
                self.end_at = datetime.now(utc)
                chat_manager.running_chat_object_id2map.pop(self.stream_id, None)
                debug_log("Chat event processing completed")

        else:
            raise RuntimeError(
                f"ChatObject of {self.stream_id} is already running or done"
            )

    async def _run(self):
        """Run chat processing flow

        Execute the main logic of message processing, including getting user information,
        processing message content, managing context length and token limitations,
        and sending responses.
        """
        debug_log("Starting chat processing flow..")
        data = self.data
        config = self.config

        data.messages.append(Message(role="user", content=self.user_input))
        debug_log(
            f"Added user message to memory, current message count: {len(data.messages)}"
        )

        self.train["content"] = (
            "<SCHEMA>\n"
            + (
                f"<HIDDEN>{config.cookie.cookie}</HIDDEN>\n"
                if config.cookie.enable_cookie
                else ""
            )
            + "Please participate in the discussion in your own character identity. Try not to use similar phrases when responding to different topics. User's messages are contained within user inputs."
            + "Your character setting is in the <SYSTEM_INSTRUCTIONS> tags, and the summary of previous conversations is in the <SUMMARY> tags."
            + "\n</SCHEMA>\n"
            + "<SYSTEM_INSTRUCTIONS>\n"
            + "\n</SYSTEM_INSTRUCTIONS>"
            + f"\n<SUMMARY>\n{data.abstract if config.llm.enable_memory_abstract else ''}\n</SUMMARY>"
        )
        debug_log(self.train["content"])

        debug_log("Starting applying memory limitations..")
        async with MemoryLimiter(self.data, self.train) as lim:
            await lim.run_enforce()
            abs_usage = lim.usage
            self.data = lim.memory
        debug_log("Memory limitation application completed")

        send_messages = self._prepare_send_messages()
        debug_log(
            f"Preparing sending messages completed, message count: {len(send_messages)}"
        )
        response: UniResponse[str, None] = await self._process_chat(send_messages)
        if response.usage and abs_usage:
            response.usage.completion_tokens += abs_usage.completion_tokens
            response.usage.prompt_tokens += abs_usage.prompt_tokens
            response.usage.total_tokens += abs_usage.total_tokens

        debug_log("Chat processing completed, preparing to send response")
        await self.set_queue_done()

    def queue_closed(self) -> bool:
        """Check if the response queue is closed

        Returns:
            True if the queue is closed, False otherwise
        """
        return self._queue_done

    async def set_queue_done(self) -> None:
        """Mark the response queue as done by putting the done marker"""
        if not self.queue_closed():
            await self.response_queue.put(self.__done_marker)

    async def yield_response(self, response: str | MessageContent):
        """Send chat model response to the queue allowing both str and MessageContent types.

        Args:
            response: Either a string or MessageContent object to be sent to the queue
        """
        if not self.queue_closed():
            await self.response_queue.put(response)
        else:
            raise RuntimeError("Queue is closed.")

    async def yield_response_iteration(
        self, iterator: AsyncGenerator[str | MessageContent, None]
    ):
        """Send chat model response to the queue allowing both str and MessageContent types.

        Args:
            iterator: An async generator that yields either strings or MessageContent objects
        """
        async for chunk in iterator:
            await self.yield_response(chunk)

    def get_response_generator(self) -> AsyncGenerator[str | MessageContent, None]:
        """Return an async generator to iterate over responses from the queue.

        Yields:
            Either a string or MessageContent object from the response queue
        """
        return self._response_generator()

    async def full_response(self) -> str:
        """Return full response from the queue as a single string.

        Returns:
            Complete response string combining all chunks in the queue
        """
        builder = StringIO()
        async for item in self.get_response_generator():
            if isinstance(item, str):
                builder.write(item)
            elif isinstance(item, MessageContent):
                builder.write(str(item.get_content()))
        return builder.getvalue()

    async def _response_generator(self) -> AsyncGenerator[str | MessageContent, None]:
        """Internal method to asynchronously yield items from the queue until done marker is reached.

        Yields:
            Items from the response queue until the done marker is encountered
        """
        while True:
            item = await self.response_queue.get()
            if item is self.__done_marker:
                self.response_queue.task_done()
                break
            yield item

    async def _process_chat(
        self,
        send_messages: CONTENT_LIST_TYPE,
    ) -> UniResponse[str, None]:
        """Call chat model to generate response and trigger related events.

        Args:
            send_messages: Send message list
            extra_usage: Extra token usage information

        Returns:
            Model response
        """
        self.last_call = datetime.now(utc)

        data = self.data
        debug_log(
            f"Starting chat processing, sending message count: {len(send_messages)}"
        )

        debug_log("Triggering matcher functions..")
        chat_event = PreCompletionEvent(
            chat_object=self,
            user_input=self.user_input,
            original_context=self.data.messages,
        )
        await MatcherManager.trigger_event(chat_event)
        self.data.messages = chat_event.get_context_messages().unwrap()

        debug_log("Calling chat model..")
        response: UniResponse[str, None] | None = None
        async for chunk in call_completion(self.data.messages):
            if isinstance(chunk, str):
                await self.yield_response(StringMessageContent(chunk))
            elif isinstance(chunk, UniResponse):
                response = chunk
            elif isinstance(chunk, MessageContent):
                await self.yield_response(chunk)
        if response is None:
            raise RuntimeError("No final response from chat adapter.")
        self.response = response
        messages = self.data.messages
        debug_log("Triggering chat events..")
        chat_event = CompletionEvent(self.user_input, messages, self, response.content)
        await MatcherManager.trigger_event(chat_event)
        response.content = chat_event.model_response
        data.messages.append(
            Message[str](
                content=response.content,
                role="assistant",
            )
        )
        debug_log(
            f"Added assistant response to memory, current message count: {len(data.messages)}"
        )

        debug_log("Chat processing completed")
        return response

    def _prepare_send_messages(
        self,
    ) -> list:
        """Prepare message list to send to the chat model, including system prompt data and context.

        Returns:
            Prepared message list to send
        """
        self.last_call = datetime.now(utc)
        debug_log("Preparing messages to send..")
        train: Message[str] = Message[str].model_validate(self.train)
        data = self.data
        messages = [Message.model_validate(train), *copy.deepcopy(data.messages)]
        debug_log(f"Messages preparation completed, total {len(messages)} messages")
        return messages

    def get_snapshot(self) -> ChatObjectMeta:
        """Get a snapshot of the chat object

        Returns:
            Chat object metadata
        """
        return ChatObjectMeta.model_validate(self, from_attributes=True)


@dataclass
class ChatManager:
    custom_menu: list[dict[str, str]] = field(default_factory=list)
    running_messages_poke: dict[str, Any] = field(default_factory=dict)
    running_chat_object: defaultdict[str, list[ChatObject]] = field(
        default_factory=lambda: defaultdict(list)
    )
    running_chat_object_id2map: dict[str, ChatObjectMeta] = field(default_factory=dict)

    def clean_obj(self, k: str, maxitems: int = 10):
        """
        Clean up running chat objects under the specified key, keeping only the first 10 objects,
        removing any excess unfinished parts

        Args:
            k (tuple[int, bool]): Key value, composed of instance ID and whether it's group chat
            maxitems (int, optional): Maximum number of objects. Defaults to 10.
        """
        objs = self.running_chat_object[k]
        if len(objs) > maxitems:
            dropped_obj = objs[maxitems:]
            objs = [obj for obj in dropped_obj if not obj.is_done()] + objs[:maxitems]
            dropped_obj = [obj for obj in dropped_obj if obj.is_done()]
            for obj in dropped_obj:
                self.running_chat_object_id2map.pop(obj.stream_id, None)
            self.running_chat_object[k] = objs

    def get_all_objs(self) -> list[ChatObjectMeta]:
        """
        Get all running chat object metadata

        Returns:
            list[ChatObjectMeta]: List of all running chat object metadata
        """
        return list(self.running_chat_object_id2map.values())

    def get_objs(self, session_id: str) -> list[ChatObject]:
        """
        Get the corresponding list of chat objects based on the session ID

        Args:
            session_id (str): User session ID

        Returns:
            list[ChatObject]: List of chat objects
        """
        return self.running_chat_object[session_id]

    async def clean_chat_objects(self, maxitems: int = 10) -> None:
        """
        Asynchronously clean up all running chat objects, limiting the number of objects for each key to no more than 10
        """
        async with LOCK:
            for key in self.running_chat_object.keys():
                self.clean_obj(key, maxitems)

    async def add_chat_object(self, chat_object: ChatObject) -> None:
        """
        Add a new chat object to the running list

        Args:
            chat_object (ChatObject): Chat object instance
        """
        async with LOCK:
            meta: ChatObjectMeta = chat_object.get_snapshot()
            self.running_chat_object_id2map[chat_object.stream_id] = meta
            key = chat_object.session_id
            self.running_chat_object[key].insert(0, chat_object)
            self.clean_obj(key)


chat_manager = ChatManager()
