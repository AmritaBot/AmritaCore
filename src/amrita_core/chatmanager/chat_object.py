import asyncio
import contextlib
import copy
from asyncio import Task
from collections.abc import Awaitable, Callable
from datetime import datetime
from functools import wraps
from io import StringIO
from types import TracebackType
from typing import Any, TypeVar
from uuid import uuid4

from amrita_sense import ALIAS, Node, NodeComposeRendered, WorkflowInterpreter
from amrita_sense.hook.matcher import MatcherFactory as MatcherManager
from amrita_sense.instructions import ARCHIVED_NODES
from amrita_sense.instructions.subprogram import SubprogramStorage
from jinja2 import Template
from pytz import utc
from typing_extensions import Self

from amrita_core.agent.context import StrategyContext
from amrita_core.agent.strategy import (
    AgentStrategy,
    NoExceptionHandler,
    StrategyLikedObject,
)
from amrita_core.builtins.agent import ReActAgentStrategy
from amrita_core.config import AmritaConfig, get_config
from amrita_core.consts import DEFAULT_TEMPLATE
from amrita_core.contents import MessageContent, MessageWithMetadata
from amrita_core.hook.event import CompletionEvent, FallbackContext, PreCompletionEvent
from amrita_core.hook.exception import FallbackFailed
from amrita_core.libchat import (
    RESPONSE_TYPE,
    call_completion,
)
from amrita_core.logging import debug_log, logger
from amrita_core.preset import PresetManager
from amrita_core.sessions import SessionData, SessionsManager
from amrita_core.streaming import SuspendObjectStream
from amrita_core.types import (
    USER_INPUT,
    Message,
    ModelPreset,
    SendMessageWrap,
    UniResponse,
    UniResponseUsage,
)
from amrita_core.types import (
    MemoryModel as Memory,
)
from amrita_core.utils import gather_usage, get_current_datetime_timestamp

from .chat_libs import ChatManager, chat_manager
from .chat_obj_meta import ChatObjectMeta
from .enums import (
    BuiltinName,
    SuspendEnum,
)
from .memory_limiter import MemoryLimiter

RESPONSE_CALLBACK_TYPE = Callable[[RESPONSE_TYPE], Awaitable[Any]] | None

# Type vars
FUNC_RET_T = TypeVar("FUNC_RET_T")


class ChatObject(SuspendObjectStream[RESPONSE_TYPE]):
    """Chat processing object - The minimal unit of chat processing.

    This class is responsible for processing a single chat session, including message receiving,
    context management, model calling, and response sending.
    """

    stream_id: str  # Chat object ID
    timestamp: str  # Timestamp (for LLM)
    time: datetime  # Time
    end_at: datetime | None = None
    data: Memory  # (lateinit) Memory file
    user_input: USER_INPUT
    user_message: Message[USER_INPUT]  # (lateinit) User message
    context_wrap: SendMessageWrap  # (lateinit) Context message
    train: Message[str]  # System message
    last_call: datetime  # Last internal function call time
    now_calling: str | None = None  # currently calling function name
    session_id: str  # Session ID
    response: UniResponse[str, None]  # (lateinit) Response
    extra_usage: UniResponseUsage[int]
    preset: ModelPreset  # preset used in this call
    config: AmritaConfig  # config used in this call
    session: SessionData | None  # (lateinit) Session data
    strategy: type[AgentStrategy] | StrategyLikedObject
    template: Template
    jinja2_vars: dict[str, Any]  # Vars will be passed to template system.
    _q_tout: float | None
    _is_running: bool = False  # Whether it is running
    _is_done: bool = False  # Whether it has completed
    _task: Task[None]
    _err: BaseException | None = None
    _hook_kwargs: dict[str, Any]
    _hook_args: tuple[Any, ...]
    _chatman: ChatManager

    _interpreter: (
        WorkflowInterpreter  # (lateinit) When _entry is called, this will be set.
    )
    _workflow: (
        NodeComposeRendered  # (lateinit) ChatObject's runtime, will be set in __init__.
    )
    _middleware: (
        Callable[[Self], Awaitable[Any]] | None
    )  # Middleware for the whole workflow, will be set in __init__.
    _raised_exc: tuple[type[BaseException], ...]

    def __init__(
        self,
        train: dict[str, str] | Message[str],
        user_input: USER_INPUT,
        context: Memory | None,
        session_id: str,
        callback: RESPONSE_CALLBACK_TYPE = None,
        config: AmritaConfig | None = None,
        preset: ModelPreset | None = None,
        auto_create_session: bool = False,
        *,
        chat_man: ChatManager | None = None,
        train_template: Template = DEFAULT_TEMPLATE,
        jinja2_vars: dict[str, Any] | None = None,
        agent_strategy: type[AgentStrategy] | StrategyLikedObject = ReActAgentStrategy,
        hook_args: tuple[Any, ...] = (),
        hook_kwargs: dict[str, Any] | None = None,
        exception_ignored: tuple[type[BaseException], ...] = (),
        middleware: Callable[[Self], Awaitable[Any]] | None = None,
        archived_nodes: SubprogramStorage | None = None,
        queue_size: int = 45,
        queue_timeout: float | None = 10.0,
    ) -> None:
        """Initialize a chat object

        Args:
            train (dict[str, str] | Message[str]): Training data (system prompts)
            user_input (USER_INPUT): Input from the user
            context (Memory | None): Memory context for the session
            session_id (str): Unique identifier for the session
            callback (RESPONSE_CALLBACK_TYPE, optional): Callback function to be called when returning response. Defaults to None.
            config (AmritaConfig | None, optional): Config used for this call. Defaults to None.
            preset (ModelPreset | None, optional): Preset used for this call. Defaults to None.
            auto_create_session (bool, optional): Whether to automatically create a session if it does not exist. Defaults to False.
            jinja2_vars (dict[str, Any] | None, optional): Variables to be passed to the template system. Defaults to None.
            chat_man (ChatManager | None, optional): ChatManager that ChatObject will be bound to. Defaults to None(Global ChatManager).
            train_template (Template, optional): Jinja2 template used to format system message.
            agent_strategy (type[AgentStrategy], optional):  Agent strategy to be used for execution. Defaults to ReActAgentStrategy.
            hook_args (tuple[Any, ...], optional): Arguments could be passed to the Matcher function. Defaults to ().
            hook_kwargs (dict[str, Any] | None, optional): Keyword arguments could be passed to the Matcher function. Defaults to None.
            middleware (Callable[[Self],Awaitable[Any]] | None, optional): Middleware for the whole workflow. Defaults to None.
            exception_ignored (tuple[type[BaseException], ...], optional): These exceptions will be raised again if they are raised in the Matcher function. Defaults to ().
            queue_size (int, optional): Maximum number of message chunks to be stored in the queue. Defaults to 45.
        """
        global chat_manager
        sm = SessionsManager()
        if auto_create_session and not sm.is_session_registered(session_id):
            sm.init_session(session_id)
        self._raised_exc = exception_ignored
        session: SessionData | None = sm.get_session_data(session_id, None)
        self.session = session
        self.train = (
            train if isinstance(train, Message) else Message[str].model_validate(train)
        )
        self.data = context or sm.get_session_data(session_id).memory
        self.session_id = session_id
        # initialize iostream
        super().__init__(
            queue_size=queue_size, callback=callback, queue_timeout=queue_timeout
        )
        # data
        self.user_input = user_input
        self.user_message = Message(role="user", content=user_input)
        self.timestamp = get_current_datetime_timestamp()
        self.time = datetime.now(utc)
        self.config: AmritaConfig = config or (
            session.config if session else get_config()
        )
        self.strategy = agent_strategy
        self.extra_usage = UniResponseUsage(
            prompt_tokens=0, completion_tokens=0, total_tokens=0
        )
        self._chatman = chat_man or chat_manager
        # other
        self.last_call = datetime.now(utc)
        self.preset = preset or (
            session.presets.get_default_preset()
            if session
            else PresetManager().get_default_preset()
        )
        self.template = train_template
        jinja2_vars = jinja2_vars or {}
        if any(name in jinja2_vars for name in ("train", "self", "memory", "chatobj")):
            raise RuntimeError("Received a reserved keyword, please use another name.")
        self.jinja2_vars = jinja2_vars
        # Hook args
        self._hook_args = hook_args
        self._hook_kwargs = hook_kwargs or {}
        self._middleware = middleware
        archived_nodes = archived_nodes or ARCHIVED_NODES()
        archived_nodes._nodes += (
            ALIAS(self._run_agent, BuiltinName.AGENT_STRATEGY.value),
        )
        self._workflow = (
            self._render_train
            >> self._limiting_memory
            >> self._prepare_messages
            >> self._pre_runner
            >> self._run_strategy
            >> self._call_completion
            >> self._post_runner
            >> (archived_nodes)
        ).render()
        self._interpreter = WorkflowInterpreter(
            self._workflow,
            self,
            exception_ignored=exception_ignored,
            extra_args=(*hook_args, self),
            extra_kwargs=hook_kwargs,
        )
        # initialize id
        self.stream_id = uuid4().hex

    @staticmethod
    def monitoring(func: Callable[..., Any]):
        """Decorator for monitoring.This decorator will ONLY BE USED in ChatObject."""

        @wraps(func)
        def inner(*args, **kwargs):
            self: ChatObject = args[0]  # This is Self
            self.last_call = datetime.now(utc)
            pev = self.now_calling
            self.now_calling = func.__name__
            try:
                return func(*args, **kwargs)
            finally:
                self.now_calling = pev

        return inner

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

    def get_exception(self) -> BaseException | None:
        """
        Get exceptions that occurred during task execution

        Returns:
            BaseException | None: Returns exception object if an exception occurred during task execution, otherwise returns None
        """
        return self._err

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

    @monitoring
    def terminate(self) -> None:
        """
        Terminate task execution
        Sets the task status to completed and cancels the internal task
        """
        self._is_done = True
        self._is_running = False
        if hasattr(self, "_task") and not self._task.done():
            self._task.cancel()

    def __await__(self):
        """
        Await for task completion
        """
        if not hasattr(self, "_task"):
            raise RuntimeError("ChatObject not running")
        return self._task.__await__()

    async def __aenter__(self) -> Self:
        if not hasattr(self, "_task"):
            raise RuntimeError("ChatObject not running")
        if self._has_consumer:
            raise RuntimeError("ChatObject already has a consumer")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        del exc_tb  # This is unused
        if exc_type is not None:
            self._err = exc_val
        self.terminate()
        await self

    @monitoring
    def begin(self) -> Self:
        """Start chat object task"""
        if not hasattr(self, "_task"):
            logger.debug("Starting chat object task...")
            self._task = asyncio.create_task(self._entry())
        return self

    @monitoring
    @SuspendObjectStream.suspend_with_tag(SuspendEnum.ENTRY_POINT.value)
    async def _entry(self) -> None:
        """Call chat object to process messages"""
        if not self._is_running and not self._is_done:
            self.stream_id = uuid4().hex
            logger.debug(f"Starting chat processing, stream ID:{self.stream_id}")

            try:
                self._is_running = True
                await self._chatman.add_chat_object(self)
                if not self._middleware:
                    await self._interpreter.run()
                else:
                    await self._middleware(self)
            finally:
                self._is_running = False
                self._is_done = True
                self.end_at = datetime.now(utc)
                self._chatman.running_chat_object_id2map.pop(self.stream_id, None)
                if self._chatman.clean_obj(
                    self.session_id, 10000
                ):  # A hard limit just to avoid memory leaks
                    logger.warning(
                        "Detected too many chat objects in session id `%s`! Please check if there are any memory leaks!",
                        self.session_id,
                    )
                logger.debug("Chat event processing completed")

        else:
            raise RuntimeError(
                f"ChatObject of {self.stream_id} is already running or done"
            )

    @Node(SuspendEnum.TRAIN_RENDER.value)
    async def _render_train(self):
        logger.debug("Starting chat processing flow..")
        data = self.data
        config = self.config

        data.messages.append(self.user_message)

        logger.debug(
            f"Added user message to memory, current message count: {len(data.messages)}"
        )
        # train,memory,chatobj(ChatObject),config will be given to Jinja2
        self.train.content = await asyncio.to_thread(
            self.template.render,
            train=self.train,
            memory=self.data,
            chatobj=self,
            config=config,
            **self.jinja2_vars,
        )
        debug_log(self.train.content)

    @Node(SuspendEnum.MEMORY.value)
    async def _limiting_memory(self):
        logger.debug("Starting applying memory limitations..")
        async with MemoryLimiter(self.data, self.train, config=self.config) as lim:
            await self._wait_for_continue(SuspendEnum.MEMORY.value)
            await lim.run_enforce()

            if abs_usage := lim.usage:
                self.extra_usage = gather_usage(self.extra_usage, abs_usage)
            self.data = lim.memory
        logger.debug("Memory limitation application completed")

    @Node(SuspendEnum.MESSAGES_PREPARED.value, wrap_to_async=False)
    def _prepare_messages(self):
        send_messages = self._prepare_send_messages()
        self.context_wrap = SendMessageWrap.validate_messages(send_messages)
        logger.debug(
            f"Preparing sending messages completed, message count: {len(send_messages)}"
        )
        """
        response: UniResponse[str, None] = await self._process_chat(send_messages)
        self.response = response

        logger.debug("Chat processing completed, preparing to send response")
        await self.set_queue_done()
        """

    @Node(SuspendEnum.PRECOMPLE.value)
    async def _pre_runner(self):
        logger.debug(
            f"Starting chat processing, sending message count: {len(self.context_wrap)}"
        )

        logger.debug("Triggering matcher functions..")
        messages = self.context_wrap
        chat_event = PreCompletionEvent(
            chat_object=self,
            user_input=self.user_input,
            original_context=messages,
        )
        await MatcherManager.trigger_event(
            chat_event,
            self.config,
            self,
            self.preset,
            *self._hook_args,
            session=self.session,
            exception_ignored=self._raised_exc,
            **self._hook_kwargs,
        )
        self.data.messages = chat_event.get_context_messages().unwrap(
            exclude_system=True
        )

    @Node(SuspendEnum.LLM_CALL.value)
    async def _call_completion(self):
        logger.debug("Calling chat model..")
        response: UniResponse[str, None] | None = None
        used_preset: set[str] = set()
        for i in range(1, self.config.llm.max_fallbacks + 1):
            try:
                used_preset.add(self.preset.name)
                async for chunk in call_completion(
                    self.context_wrap.unwrap(), config=self.config, preset=self.preset
                ):
                    if isinstance(chunk, UniResponse):
                        response = chunk
                    elif isinstance(chunk, MessageContent | str):
                        await self.yield_response(chunk)
                break
            except Exception as e:
                logger.warning(
                    f"Because of `{e!s}`, LLM request failed, retrying ({i}/{self.config.llm.max_retries})..."
                )
                ctx = FallbackContext(self.preset, e, self.config, self.context_wrap, i)
                await MatcherManager.trigger_event(
                    ctx, ctx.config, exception_ignored=(FallbackFailed,)
                )
                if ctx.preset is self.preset:
                    ctx.fail("No preset fallback available, exiting!")
                self.preset = ctx.preset
        else:
            raise FallbackFailed("Max preset fallbacks retries exceeded.")
        if response is None:
            raise RuntimeError("No final response from chat adapter.")
        self.response = response

    @Node(SuspendEnum.COMPLE.value)
    async def _post_runner(self):
        logger.debug("Triggering chat events..")
        chat_event = CompletionEvent(
            self.user_input, self.context_wrap, self, self.response.content
        )
        await self._wait_for_continue(SuspendEnum.COMPLE.value)
        await MatcherManager.trigger_event(
            chat_event,
            self.config,
            self,
            self.preset,
            *self._hook_args,
            session=self.session,
            exception_ignored=self._raised_exc,
            **self._hook_kwargs,
        )
        self.response.content = chat_event.model_response
        self.context_wrap.append(
            Message[str](
                content=self.response.content,
                role="assistant",
            )
        )
        logger.debug(
            f"Added assistant response to memory, current message count: {len(self.context_wrap)}"
        )

        logger.debug("Chat processing completed")

    @Node(SuspendEnum.STRATEGY_START.value)
    async def _run_strategy(self, intp: WorkflowInterpreter) -> None:
        """Run workflow of strategy given."""

        match self.strategy.get_category():
            case "agent-mixed" | "agent":
                context = (
                    SendMessageWrap.validate_messages([self.train, self.user_message])
                    if self.config.function_config.use_minimal_context
                    else self.context_wrap.copy()
                )
                ctx = StrategyContext(self.user_input, context, self)
                return await intp.call_sub(
                    intp.find_addr_alias(BuiltinName.AGENT_STRATEGY.value), ctx
                )

            case "rag":
                context = SendMessageWrap.validate_messages(
                    [
                        self.train,
                        self.user_message,
                    ]
                )
            case "workflow":
                context = self.context_wrap.copy()
            case _:
                raise RuntimeError("Invalid agent strategy")
        ctx = StrategyContext(self.user_input, context, self)
        st = self.strategy(ctx)
        try:
            await st.run()
        except Exception as e:
            if isinstance(e, self._raised_exc):
                raise
            with contextlib.suppress(NoExceptionHandler):
                await st.on_exception(e)
        else:
            await st.on_post_process()
        self.context_wrap.extend(ctx.original_context.end_messages)

    @Node()
    async def _run_agent(self, ctx: StrategyContext) -> None:
        strategy: AgentStrategy | StrategyLikedObject = self.strategy(ctx)
        backup: SendMessageWrap = self.context_wrap.copy()
        try:
            for _ in range(1, self.config.function_config.agent_tool_call_limit + 1):
                await self._wait_for_continue(SuspendEnum.SINGLE_TOOL.value)
                if not (await strategy.single_execute()):
                    break
            else:
                await strategy.on_limited()
            await strategy.on_post_process()
            self.context_wrap.extend(strategy.ctx.original_context.end_messages)

        except Exception as e:
            if isinstance(e, self._raised_exc):
                raise
            logger.warning(
                f"ERROR\n{e!s}\n!Failed to call Tools! Continuing with old data..."
            )
            await self.yield_response(
                MessageWithMetadata(
                    content=f"Agent run failed:{e!s}",
                    metadata={"type": "error", "error": e},
                )
            )
            await strategy.on_exception(e)
            self.context_wrap = backup

    def _prepare_send_messages(
        self,
    ) -> list:
        """Prepare message list to send to the chat model, including system prompt data and context.

        Returns:
            Prepared message list to send
        """
        logger.debug("Preparing messages to send..")
        train: Message[str] = Message[str].model_validate(self.train)
        data = self.data
        messages = [train, *copy.deepcopy(data.messages)]
        logger.debug(f"Messages preparation completed, total {len(messages)} messages")
        return messages

    def get_snapshot(self) -> ChatObjectMeta:
        """Get a snapshot of the chat object

        Returns:
            Chat object metadata
        """
        return ChatObjectMeta.model_validate(self, from_attributes=True)
