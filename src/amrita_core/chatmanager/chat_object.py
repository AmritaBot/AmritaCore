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

from amrita_sense import (
    ALIAS,
    NOP,
    WHILE,
    Node,
    NodeCompose,
    NodeComposeRendered,
    WorkflowInterpreter,
)
from amrita_sense._unsafe import __flags__
from amrita_sense.exceptions import BreakLoop
from amrita_sense.hook.matcher import MatcherFactory as MatcherManager
from amrita_sense.instructions import GOTO
from amrita_sense.instructions.subprogram import SubprogramStorage
from amrita_sense.node.core import Node as NodeType
from jinja2 import Template
from pytz import utc
from typing_extensions import Self, deprecated

from amrita_core.agent.context import StrategyContext
from amrita_core.agent.strategy import (
    AgentStrategy,
    NoExceptionHandler,
    StrategyLikedObject,
)
from amrita_core.builtins.agent import ReActAgentStrategy
from amrita_core.config import AmritaConfig, get_config
from amrita_core.consts import DEFAULT_TEMPLATE
from amrita_core.contents import (
    MessageContent,
    MessageMetadataPayloadError,
    MessageWithMetadata,
)
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


class ChatObject:
    """Chat processing object - The minimal unit of chat processing.

    This class is responsible for processing a single chat session, including message receiving,
    context management, model calling, and response sending.
    """

    # Identity
    stream_id: str  # Chat object ID
    session_id: str  # Session ID

    # Timing
    timestamp: str  # Timestamp (for LLM)
    time: datetime  # Time
    end_at: datetime | None = None
    last_call: datetime  # Last internal function call time
    now_calling: str | None = None  # currently calling function name

    # Config & Preset
    config: AmritaConfig  # config used in this call
    preset: ModelPreset  # preset used in this call
    session: SessionData | None  # (lateinit) Session data
    strategy: type[AgentStrategy] | StrategyLikedObject

    # Input / Data
    user_input: USER_INPUT
    user_message: Message[USER_INPUT]  # (lateinit) User message
    data: Memory  # (lateinit) Memory file
    train: Message[str]  # System message
    template: Template
    jinja2_vars: dict[str, Any]  # Vars will be passed to template system.

    # IO-Stream
    io_stream: SuspendObjectStream[RESPONSE_TYPE]

    # Context
    context_wrap: SendMessageWrap  # (lateinit) Context message

    # Response
    response: UniResponse[str, None]  # (lateinit) Response
    extra_usage: UniResponseUsage[int]

    # Runtime State
    _is_running: bool = False  # Whether it is running
    _is_done: bool = False  # Whether it has completed
    _task: Task[None]
    _err: BaseException | None = None
    _q_tout: float | None

    # Hooks
    _hook_args: tuple[Any, ...]
    _hook_kwargs: dict[str, Any]
    _raised_exc: tuple[type[BaseException], ...]

    # Workflow / Interpreter
    _workflow: (
        NodeComposeRendered  # (lateinit) ChatObject's runtime, will be set in __init__.
    )
    _interpreter: (
        WorkflowInterpreter  # (lateinit) When _entry is called, this will be set.
    )
    _middleware: (
        Callable[[Self], Awaitable[Any]] | None
    )  # Middleware for the whole workflow, will be set in __init__.

    # Agent Temp (lateinit)
    _tmp_strategy: AgentStrategy | StrategyLikedObject
    _ctx_backup_tmp: SendMessageWrap
    _stg_ctx_tmp: StrategyContext

    # Manager
    _chatman: ChatManager

    def __init__(
        self,
        train: dict[str, str] | Message[str],
        user_input: USER_INPUT,
        context: Memory | None,
        session_id: str,
        config: AmritaConfig | None = None,
        preset: ModelPreset | None = None,
        auto_create_session: bool = False,
        *,
        chat_man: ChatManager | None = None,
        train_template: Template = DEFAULT_TEMPLATE,
        io_stream: SuspendObjectStream[RESPONSE_TYPE] | None = None,
        jinja2_vars: dict[str, Any] | None = None,
        agent_strategy: type[AgentStrategy] | StrategyLikedObject = ReActAgentStrategy,
        hook_args: tuple[Any, ...] = (),
        hook_kwargs: dict[str, Any] | None = None,
        exception_ignored: tuple[type[BaseException], ...] = (),
        middleware: Callable[[Self], Awaitable[Any]] | None = None,
        archived_nodes: SubprogramStorage | None = None,
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
        """
        global chat_manager
        sm = SessionsManager()
        if auto_create_session and not sm.is_session_registered(session_id):
            sm.init_session(session_id)
        self._raised_exc = (
            exception_ignored if not __flags__.DISABLE_EXC_IGNORED else ()
        )
        session: SessionData | None = sm.get_session_data(session_id, None)
        self.session = session
        self.train = (
            train if isinstance(train, Message) else Message[str].model_validate(train)
        )
        self.data = context or sm.get_session_data(session_id).memory
        self.session_id = session_id
        # initialize iostream
        self.io_stream = io_stream or SuspendObjectStream()
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
        hook_kwargs = hook_kwargs or {}
        self._hook_kwargs = hook_kwargs
        self._hook_args = hook_args
        self._middleware = middleware
        # Workflow system
        wkfl = None
        if archived_nodes is not None:
            wkfl = NodeCompose(*_workflow._graph) >> archived_nodes
        self._workflow = wkfl.render() if wkfl else _workflow_rendered
        self._interpreter = WorkflowInterpreter(
            self._workflow,
            self.io_stream,
            exception_ignored=exception_ignored,
            extra_args=(*hook_args, self),
            extra_kwargs=hook_kwargs,
        )
        # initialize id
        self.stream_id = uuid4().hex

    # Dunder / Magic methods

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
        if self.io_stream._has_consumer:
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

    # Monitoring

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

    # Public API

    @monitoring
    def begin(self) -> Self:
        """Start chat object task"""
        if not hasattr(self, "_task"):
            logger.debug("Starting chat object task...")
            self._task = asyncio.create_task(self._entry())
        return self

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

    # Backward-compatible SuspendObjectStream forwarding methods (will be removed in 0.10.0)

    @deprecated("Will be removed in 0.10.0. Use io_stream.queue_closed() instead.")
    def queue_closed(self) -> bool:
        """Check if the response queue is closed."""
        return self.io_stream.queue_closed()

    @deprecated("Will be removed in 0.10.0. Use io_stream.set_queue_done() instead.")
    async def set_queue_done(self) -> None:
        """Mark the response queue as done."""
        await self.io_stream.set_queue_done()

    @deprecated("Will be removed in 0.10.0. Use io_stream.push_object() instead.")
    async def push_object(self, obj: RESPONSE_TYPE) -> None:
        """Push an object to the sending queue."""
        await self.io_stream.push_object(obj)

    @deprecated("Will be removed in 0.10.0. Use io_stream.yield_response() instead.")
    async def yield_response(self, response: RESPONSE_TYPE) -> None:
        """Send response to the sending queue."""
        await self.io_stream.yield_response(response)

    @deprecated("Will be removed in 0.10.0. Use io_stream.set_callback_func() instead.")
    def set_callback_func(self, func: RESPONSE_CALLBACK_TYPE) -> None:
        """Set a callback function to be executed when a response is yielded."""
        self.io_stream.set_callback_func(func)  # pyright: ignore[reportArgumentType]

    @deprecated(
        "Will be removed in 0.10.0. Use io_stream.set_callback_fun_sending() instead."
    )
    def set_callback_fun_sending(self, func: RESPONSE_CALLBACK_TYPE) -> None:
        """Set a callback function to be executed when a response is sent for producer."""
        self.io_stream.set_callback_fun_sending(func)  # pyright: ignore[reportArgumentType]

    @deprecated(
        "Will be removed in 0.10.0. Use io_stream.yield_response_iteration() instead."
    )
    async def yield_response_iteration(self, iterator: Any) -> None:
        """Send chat model response to the queue from an async generator."""
        await self.io_stream.yield_response_iteration(iterator)

    @deprecated(
        "Will be removed in 0.10.0. Use io_stream.get_response_generator() instead."
    )
    def get_response_generator(self) -> Any:
        """Return an async generator to iterate over responses from the queue."""
        return self.io_stream.get_response_generator()

    @deprecated("Will be removed in 0.10.0. Use io_stream.wait_to_suspend() instead.")
    async def wait_to_suspend(self, *tags: str, timeout: float | None = None) -> None:
        """Tell SuspendObjectStream to suspend and wait for it."""
        await self.io_stream.wait_to_suspend(*tags, timeout=timeout)

    @deprecated("Will be removed in 0.10.0. Use io_stream.resume() instead.")
    def resume(self) -> None:
        """Resume to run when suspend."""
        self.io_stream.resume()

    async def full_response(self) -> str:
        """Return full response from the queue as a single string.

        Returns:
            Complete response string combining all chunks in the queue
        """
        builder = StringIO()
        async for item in self.io_stream.get_response_generator():
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

    def get_snapshot(self) -> ChatObjectMeta:
        """Get a snapshot of the chat object

        Returns:
            Chat object metadata
        """
        return ChatObjectMeta.model_validate(self, from_attributes=True)

    # Entry point

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

    # Private helpers

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

    # Workflow nodes (in execution order)


@Node(SuspendEnum.TRAIN_RENDER.value)
async def _render_train(chat_obj: ChatObject):
    logger.debug("Starting chat processing flow..")
    data = chat_obj.data
    config = chat_obj.config

    data.messages.append(chat_obj.user_message)

    logger.debug(
        f"Added user message to memory, current message count: {len(data.messages)}"
    )
    # train,memory,chatobj(ChatObject),config will be given to Jinja2
    chat_obj.train.content = await asyncio.to_thread(
        chat_obj.template.render,
        train=chat_obj.train,
        memory=chat_obj.data,
        chatobj=chat_obj,
        config=config,
        **chat_obj.jinja2_vars,
    )
    debug_log(chat_obj.train.content)


@Node(SuspendEnum.MEMORY.value)
async def _limiting_memory(chat_obj: ChatObject):
    logger.debug("Starting applying memory limitations..")
    async with MemoryLimiter(
        chat_obj.data, chat_obj.train, config=chat_obj.config
    ) as lim:
        await chat_obj.io_stream._wait_for_continue(SuspendEnum.MEMORY.value)
        await lim.run_enforce()

        if abs_usage := lim.usage:
            chat_obj.extra_usage = gather_usage(chat_obj.extra_usage, abs_usage)
        chat_obj.data = lim.memory
    logger.debug("Memory limitation application completed")


@Node(SuspendEnum.MESSAGES_PREPARED.value, wrap_to_async=False)
def _prepare_messages(chat_obj: ChatObject):
    send_messages = chat_obj._prepare_send_messages()
    chat_obj.context_wrap = SendMessageWrap.validate_messages(send_messages)
    logger.debug(
        f"Preparing sending messages completed, message count: {len(send_messages)}"
    )


@Node(SuspendEnum.PRECOMPLE.value)
async def _pre_runner(chat_obj: ChatObject):
    logger.debug(
        f"Starting chat processing, sending message count: {len(chat_obj.context_wrap)}"
    )

    logger.debug("Triggering matcher functions..")
    messages = chat_obj.context_wrap
    chat_event = PreCompletionEvent(
        chat_object=chat_obj,
        user_input=chat_obj.user_input,
        original_context=messages,
    )
    await MatcherManager.trigger_event(
        chat_event,
        chat_obj.config,
        chat_obj,
        chat_obj.preset,
        *chat_obj._hook_args,
        session=chat_obj.session,
        exception_ignored=chat_obj._raised_exc,
        **chat_obj._hook_kwargs,
    )
    chat_obj.data.messages = chat_event.get_context_messages().unwrap(
        exclude_system=True
    )


@Node(SuspendEnum.STRATEGY_START.value)
async def _run_strategy(chat_obj: ChatObject, intp: WorkflowInterpreter) -> None:
    """Run workflow of strategy given."""

    match chat_obj.strategy.get_category():
        case "agent-mixed" | "agent":
            context = (
                SendMessageWrap.validate_messages(
                    [chat_obj.train, chat_obj.user_message]
                )
                if chat_obj.config.function_config.use_minimal_context
                else chat_obj.context_wrap.copy()
            )
            ctx = StrategyContext(chat_obj.user_input, context, chat_obj)
            chat_obj._stg_ctx_tmp = ctx
            return intp.jump_to(intp.find_addr_alias(BuiltinName.AGENT_STRATEGY.value))

        case "rag":
            context = SendMessageWrap.validate_messages(
                [
                    chat_obj.train,
                    chat_obj.user_message,
                ]
            )
        case "workflow":
            context = chat_obj.context_wrap.copy()
        case _:
            raise RuntimeError("Invalid agent strategy")
    ctx = StrategyContext(chat_obj.user_input, context, chat_obj)
    st = chat_obj.strategy(ctx)
    try:
        await st.run()
    except Exception as e:
        if isinstance(e, chat_obj._raised_exc):
            raise
        with contextlib.suppress(NoExceptionHandler):
            await st.on_exception(e)
    else:
        await st.on_post_process()
    chat_obj.context_wrap.extend(ctx.original_context.end_messages)


@Node()
def _agent_entry(chat_obj: ChatObject) -> None:
    chat_obj._tmp_strategy = chat_obj.strategy(chat_obj._stg_ctx_tmp)
    chat_obj._ctx_backup_tmp = chat_obj.context_wrap.copy()


def _counter_factory() -> NodeType[None]:

    now = 1

    @Node(SuspendEnum.ADVANCE_COUNTER, False)
    async def advance(chat_obj: ChatObject):
        nonlocal now
        max_times: int = chat_obj.config.function_config.agent_tool_call_limit + 1
        if now > max_times:
            await chat_obj._tmp_strategy.on_limited()
            raise BreakLoop(f"Counter has reached the maximum limit of {max_times}")
        now += 1

    return advance


@Node(SuspendEnum.SINGLE_TOOL.value)
async def _single_strategy_exec(chat_obj: ChatObject) -> bool:
    try:
        return await chat_obj._tmp_strategy.single_execute()
    except Exception as e:
        if isinstance(e, chat_obj._raised_exc) or isinstance(
            e, chat_obj._interpreter._exc_ignored
        ):
            raise
        logger.warning(
            f"ERROR\n{e!s}\n!Failed to call Strategy! Continuing with old data..."
        )
        await chat_obj.io_stream.yield_response(
            MessageWithMetadata(
                content=f"Agent run failed:{e!s}",
                metadata=MessageMetadataPayloadError(
                    error=str(e), type="error", extra_type=None
                ),
            )
        )
        await chat_obj._tmp_strategy.on_exception(e)
        chat_obj.context_wrap = chat_obj._ctx_backup_tmp
        return False


@Node()
async def _strategy_post(chat_obj: ChatObject):
    await chat_obj._tmp_strategy.on_post_process()
    chat_obj.context_wrap.extend(
        chat_obj._tmp_strategy.ctx.original_context.end_messages
    )
    del chat_obj._tmp_strategy
    del chat_obj._ctx_backup_tmp
    del chat_obj._stg_ctx_tmp


@Node(SuspendEnum.LLM_CALL.value)
async def _call_completion(chat_obj: ChatObject):
    logger.debug("Calling chat model..")
    response: UniResponse[str, None] | None = None
    used_preset: set[str] = set()
    for i in range(1, chat_obj.config.llm.max_fallbacks + 1):
        try:
            used_preset.add(chat_obj.preset.name)
            async for chunk in call_completion(
                chat_obj.context_wrap.unwrap(),
                config=chat_obj.config,
                preset=chat_obj.preset,
            ):
                if isinstance(chunk, UniResponse):
                    response = chunk
                elif isinstance(chunk, MessageContent | str):
                    await chat_obj.io_stream.yield_response(chunk)
            break
        except Exception as e:
            logger.warning(
                f"Because of `{e!s}`, LLM request failed, retrying ({i}/{chat_obj.config.llm.max_retries})..."
            )
            ctx = FallbackContext(
                chat_obj.preset, e, chat_obj.config, chat_obj.context_wrap, i
            )
            await MatcherManager.trigger_event(
                ctx, ctx.config, exception_ignored=(FallbackFailed,)
            )
            if ctx.preset is chat_obj.preset:
                ctx.fail("No preset fallback available, exiting!")
            chat_obj.preset = ctx.preset
    else:
        raise FallbackFailed("Max preset fallbacks retries exceeded.")
    if response is None:
        raise RuntimeError("No final response from chat adapter.")
    chat_obj.response = response


@Node(SuspendEnum.COMPLE.value)
async def _post_runner(chat_obj: ChatObject):
    logger.debug("Triggering chat events..")
    chat_event = CompletionEvent(
        chat_obj.user_input, chat_obj.context_wrap, chat_obj, chat_obj.response.content
    )
    await chat_obj.io_stream._wait_for_continue(SuspendEnum.COMPLE.value)
    await MatcherManager.trigger_event(
        chat_event,
        chat_obj.config,
        chat_obj,
        chat_obj.preset,
        *chat_obj._hook_args,
        session=chat_obj.session,
        exception_ignored=chat_obj._raised_exc,
        **chat_obj._hook_kwargs,
    )
    chat_obj.response.content = chat_event.model_response
    chat_obj.context_wrap.append(
        Message[str](
            content=chat_obj.response.content,
            role="assistant",
        )
    )
    logger.debug(
        f"Added assistant response to memory, current message count: {len(chat_obj.context_wrap)}"
    )

    logger.debug("Chat processing completed")


# pre-compile workflows
_workflow: NodeCompose = (
    _render_train
    >> _limiting_memory
    >> _prepare_messages
    >> _pre_runner
    >> _run_strategy
    >> (
        GOTO(BuiltinName.STRATEGY_EOF)
        >> ALIAS(_agent_entry, BuiltinName.AGENT_STRATEGY)
        >> WHILE(_single_strategy_exec).ACTION(_counter_factory())
        >> _strategy_post
        >> ALIAS(NOP, BuiltinName.STRATEGY_EOF)
    )
    >> _call_completion
    >> _post_runner
)
_workflow_rendered = _workflow.render()
