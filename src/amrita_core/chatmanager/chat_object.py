import asyncio
import contextlib
import copy
from asyncio import Task
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
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
from amrita_sense.logging import debug_log, logger
from amrita_sense.streaming import SuspendObjectStream
from jinja2 import Template
from pytz import utc
from typing_extensions import Self

from amrita_core.agent.context import StrategyContext
from amrita_core.agent.strategy import (
    AgentStrategy,
    NoExceptionHandler,
    StrategyLikedObject,
)
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.agent import ReActAgentStrategy
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.config import AmritaConfig, get_config
from amrita_core.consts import DEFAULT_TEMPLATE
from amrita_core.contents import (
    MessageContent,
    MessageMetadataPayloadError,
    MessageWithMetadata,
)
from amrita_core.contexts import StateContext
from amrita_core.hook.event import CompletionEvent, FallbackContext, PreCompletionEvent
from amrita_core.hook.exception import FallbackFailed
from amrita_core.libchat import (
    RESPONSE_TYPE,
    call_completion,
)
from amrita_core.types import (
    USER_INPUT,
    Message,
    ModelPreset,
    SendMessageWrap,
    UniResponse,
    UniResponseUsage,
)
from amrita_core.types.memory import MemoryModel
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


@dataclass
class AgentLoopState:
    """Transient state for the framework-managed agent loop."""

    stg_ctx: StrategyContext
    strategy: AgentStrategy | StrategyLikedObject | None = None
    ctx_backup: SendMessageWrap | None = None
    called_count: int = 0


@dataclass
class DatabackendOptions:
    """Transient state for the framework-managed fetch strategy."""

    skip_memory_fetch: bool = False
    skip_tools_fetch: bool = False
    skip_mcp_fetch: bool = False
    skip_presets_fetch: bool = False
    skip_ability_extra_setting: bool = False
    skip_memory_commit: bool = False


class ChatObject:
    """Chat processing object - The minimal unit of chat processing.

    This class is responsible for processing a single chat session, including message receiving,
    context management, model calling, and response sending.
    """

    # Identity
    stream_id: str  # Chat object ID
    _s_id: str  # Temprorary session ID if assigned `session_id`

    # Timing
    timestamp: str  # Timestamp (for LLM)
    time: datetime  # Time
    end_at: datetime | None
    last_call: datetime  # Last internal function call time
    now_calling: str | None  # currently calling function name

    # Config & Preset
    config: AmritaConfig  # config used in this call
    preset: ModelPreset  # (lateinit) preset used in this call, set on runtime
    strategy: type[AgentStrategy] | StrategyLikedObject

    # Core State
    slot: BackendSlots
    state: StateContext  # (lateinit) state of chat_obj will be set in runtime.

    # Input / Data
    user_input: USER_INPUT
    user_message: Message[USER_INPUT]  # User message
    train: Message[str]  # System message
    template: Template
    jinja2_vars: dict[str, Any]  # Vars will be passed to template system.
    context_wrap: SendMessageWrap

    # IO-Stream
    io_stream: SuspendObjectStream[RESPONSE_TYPE]
    # Response
    response: UniResponse[str, None]  # (lateinit) Response
    extra_usage: UniResponseUsage[int]

    # Runtime State
    _is_running: bool  # Whether it is running
    _is_done: bool  # Whether it has completed
    _task: Task[None]  # (lateinit) set on runtime
    _err: BaseException | None  # Exception in runtime

    # Options
    _bke_opt: DatabackendOptions
    # Args for DI system
    _hook_args: tuple[Any, ...]
    _hook_kwargs: dict[str, Any]
    _raised_exc: tuple[type[BaseException], ...]

    # Workflow / Interpreter
    _workflow: NodeComposeRendered
    _interpreter: WorkflowInterpreter
    _middleware: (
        Callable[[Self], Awaitable[Any]] | None
    )  # Middleware for the whole workflow, will be set in __init__.

    # Agent loop state
    _agent_loop: AgentLoopState | None

    # ChatObject temp storage
    _chatman: ChatManager
    __slots__ = (
        "_agent_loop",
        "_bke_opt",
        "_chatman",
        "_err",
        "_hook_args",
        "_hook_kwargs",
        "_interpreter",
        "_is_done",
        "_is_running",
        "_middleware",
        "_raised_exc",
        "_s_id",
        "_task",
        "_workflow",
        "config",
        "context_wrap",
        "end_at",
        "extra_usage",
        "io_stream",
        "jinja2_vars",
        "last_call",
        "now_calling",
        "preset",
        "response",
        "slot",
        "state",
        "strategy",
        "stream_id",
        "template",
        "time",
        "timestamp",
        "train",
        "user_input",
        "user_message",
    )

    def __init__(
        self,
        train: dict[str, str] | Message[str],
        user_input: USER_INPUT,
        context: StateContext | None = None,
        session_id: str | None = None,
        config: AmritaConfig | None = None,
        preset: ModelPreset | None = None,
        *,
        backend: BackendSlots | None = None,
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
        backend_options: DatabackendOptions | None = None,
    ) -> None:
        """Initialize a chat object

        Args:
            train: Training data (system prompts).
            user_input: Input from the user.
            context: Pre-built state context. Mutually exclusive with ``session_id``.
            session_id: Unique identifier for the session. Mutually exclusive with
                ``context``. When both are None, ChatObject requires ``session_id``
                to create a new StateContext at runtime.
            config: Config used for this call. Defaults to global config.
            preset: Preset used for this call. Defaults to None (resolved at runtime).
            backend: Backend slots for memory and ability I/O. Defaults to
                LegacyBackend for both slots.
            chat_man: ChatManager that ChatObject will be bound to.
                Defaults to the global ChatManager.
            train_template: Jinja2 template used to format the system message.
            io_stream: External SuspendObjectStream instance.
                If None, a new one is created automatically.
            jinja2_vars: Variables to be passed to the template system.
            agent_strategy: Agent strategy to be used for execution.
                Accepts a strategy class or a pre-initialised StrategyLikedObject
                instance. Defaults to ReActAgentStrategy.
            hook_args: Positional arguments passed to event handlers.
            hook_kwargs: Keyword arguments passed to event handlers.
            exception_ignored: Exception types that should be re-raised
                if caught in event handlers.
            middleware: Async middleware for the whole workflow.
            archived_nodes: Additional node subprograms appended after the
                standard pipeline.
            backend_options: Fine-grained control over which backend
                fetch/commit operations are performed.
        """
        # Init as None in slots
        self._agent_loop = None
        self._err = None
        self._is_done = False
        self._is_running = False
        self.now_calling = None
        self.end_at = None
        # Special flags
        self._raised_exc = (
            exception_ignored if not __flags__.DISABLE_EXC_IGNORED else ()
        )
        self.last_call = datetime.now(utc)
        # initialize id
        self.stream_id = uuid4().hex

        # initialize iostream
        self.io_stream = io_stream or SuspendObjectStream()
        # data
        if not context and not session_id:
            raise ValueError("Either context or session_id must be provided")
        if session_id:
            if context:
                raise ValueError("Both context and session_id cannot be provided")
            self._s_id = session_id
        self.train = (
            train if isinstance(train, Message) else Message[str].model_validate(train)
        )
        if context:
            self.state = context
        if preset:
            self.preset = preset
        if backend:
            self.slot = backend
        else:
            bknd = LegacyBackend()
            self.slot = BackendSlots(bknd, bknd)
        self.user_input = user_input
        self.user_message = Message(role="user", content=user_input)
        self.timestamp = get_current_datetime_timestamp()
        self.time = datetime.now(utc)
        self.config = config or get_config()
        self.strategy = agent_strategy
        self.extra_usage = UniResponseUsage(
            prompt_tokens=0, completion_tokens=0, total_tokens=0
        )
        # other
        self._chatman = chat_man or chat_manager
        self._agent_loop = None
        self.template = train_template
        jinja2_vars = jinja2_vars or {}
        if any(name in jinja2_vars for name in ("train", "self", "memory", "chatobj")):
            raise RuntimeError("Received a reserved keyword, please use another name.")
        self.jinja2_vars = jinja2_vars
        # Options
        self._bke_opt = backend_options or DatabackendOptions()
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

    # Properties
    @property
    def session_id(self) -> str:
        """
        Get the session ID for the workflow.
        Falls back to ``_s_id`` if state has not been initialized yet.
        """
        if not hasattr(self, "state"):
            return self._s_id
        return self.state.session_id

    @property
    def data(self) -> MemoryModel:
        """
        Get the memory model for the workflow
        """
        if not hasattr(self, "state"):
            raise RuntimeError("The state of ChatObject hasn't initialized")
        return self.state.memory

    @data.setter
    def data(self, val: MemoryModel):
        if not hasattr(self, "state"):
            object.__setattr__(
                self,
                "state",
                StateContext(self._s_id if hasattr(self, "_s_id") else ""),
            )
        self.state.memory = val

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
    async def _entry(self) -> None:
        """Call chat object to process messages"""
        await self.io_stream._wait_for_continue(SuspendEnum.ENTRY_POINT)
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


@Node(SuspendEnum.LOAD_STATE)
async def _load_state(chat_obj: ChatObject):
    logger.debug("Loading state..")
    if not hasattr(chat_obj, "state"):
        if not hasattr(chat_obj, "_s_id"):
            raise RuntimeError("Session id is not assigned, cannot load state.")
        chat_obj.state = StateContext(chat_obj._s_id)
    opt = chat_obj._bke_opt
    slot = chat_obj.slot
    if not (
        opt.skip_mcp_fetch
        or opt.skip_ability_extra_setting
        or opt.skip_tools_fetch
        or opt.skip_presets_fetch
    ):
        chat_obj.state.ability = await slot.ability.load_ability_all(
            chat_obj.state.session_id
        )
    else:
        if not opt.skip_mcp_fetch:
            chat_obj.state.ability.mcp = await slot.ability.load_mcp_clients(
                chat_obj.state.session_id
            )
        if not opt.skip_tools_fetch:
            chat_obj.state.ability.tools = await slot.ability.load_tools(
                chat_obj.state.session_id
            )
        if not opt.skip_presets_fetch:
            chat_obj.state.ability.presets = await slot.ability.load_presets(
                chat_obj.state.session_id
            )
    if not (opt.skip_memory_fetch):
        chat_obj.state.memory = await slot.memory.load_memory(chat_obj.state.session_id)
    if not hasattr(chat_obj, "preset"):
        chat_obj.preset = chat_obj.state.ability.presets.get_default_preset()


@Node(SuspendEnum.TRAIN_RENDER)
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


@Node(SuspendEnum.MEMORY)
async def _limiting_memory(chat_obj: ChatObject):
    logger.debug("Starting applying memory limitations..")
    async with MemoryLimiter(
        chat_obj.data, chat_obj.train, config=chat_obj.config
    ) as lim:
        await chat_obj.io_stream._wait_for_continue(SuspendEnum.MEMORY)
        await lim.run_enforce()

        if abs_usage := lim.usage:
            chat_obj.extra_usage = gather_usage(chat_obj.extra_usage, abs_usage)
        chat_obj.data = lim.memory
    logger.debug("Memory limitation application completed")


@Node(SuspendEnum.MESSAGES_PREPARED, wrap_to_async=False)
def _prepare_messages(chat_obj: ChatObject):
    send_messages = chat_obj._prepare_send_messages()
    chat_obj.context_wrap = SendMessageWrap.validate_messages(send_messages)
    logger.debug(
        f"Preparing sending messages completed, message count: {len(send_messages)}"
    )


@Node(SuspendEnum.PRECOMPLE)
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
        state=chat_obj.state,
        slot=chat_obj.slot,
        exception_ignored=chat_obj._raised_exc,
        **chat_obj._hook_kwargs,
    )
    chat_obj.data.messages = chat_event.get_context_messages().unwrap(
        exclude_system=True
    )


@Node(SuspendEnum.STRATEGY_START)
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
            chat_obj._agent_loop = AgentLoopState(stg_ctx=ctx)
            return intp.jump_to(intp.find_addr_alias(BuiltinName.AGENT_STRATEGY))

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
    loop = chat_obj._agent_loop
    assert loop is not None
    loop.strategy = chat_obj.strategy(loop.stg_ctx)
    loop.ctx_backup = chat_obj.context_wrap.copy()


@Node(SuspendEnum.ADVANCE_COUNTER, False)
async def _advance_ctr(chat_obj: ChatObject):
    loop = chat_obj._agent_loop
    assert loop is not None
    assert loop.strategy is not None
    max_times: int = chat_obj.config.function_config.agent_tool_call_limit + 1
    if loop.called_count > max_times:
        await loop.strategy.on_limited()
        raise BreakLoop(f"Counter has reached the maximum limit of {max_times}")
    loop.called_count += 1


@Node(SuspendEnum.SINGLE_TOOL)
async def _single_strategy_exec(chat_obj: ChatObject) -> bool:
    loop = chat_obj._agent_loop
    assert loop is not None
    assert loop.strategy is not None
    try:
        return await loop.strategy.single_execute()
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
        await loop.strategy.on_exception(e)
        assert loop.ctx_backup is not None
        chat_obj.context_wrap = loop.ctx_backup
        return False


@Node()
async def _strategy_post(chat_obj: ChatObject):
    loop = chat_obj._agent_loop
    assert loop is not None
    assert loop.strategy is not None
    await loop.strategy.on_post_process()
    chat_obj.context_wrap.extend(loop.strategy.ctx.original_context.end_messages)
    chat_obj._agent_loop = None


@Node(SuspendEnum.LLM_CALL)
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


@Node(SuspendEnum.COMPLE)
async def _post_runner(chat_obj: ChatObject):
    logger.debug("Triggering chat events..")
    chat_event = CompletionEvent(
        chat_obj.user_input, chat_obj.context_wrap, chat_obj, chat_obj.response.content
    )
    await chat_obj.io_stream._wait_for_continue(SuspendEnum.COMPLE)
    await MatcherManager.trigger_event(
        chat_event,
        chat_obj.config,
        chat_obj,
        chat_obj.preset,
        *chat_obj._hook_args,
        state=chat_obj.state,
        slot=chat_obj.slot,
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


@Node(SuspendEnum.COMMIT_MEMORY)
async def _commit_memory(chat_obj: ChatObject) -> None:
    opt = chat_obj._bke_opt
    if not opt.skip_memory_commit:
        await chat_obj.slot.memory.commit_memory(chat_obj.session_id, chat_obj.data)


# pre-compile workflows
_workflow: NodeCompose = (
    _load_state
    >> _render_train
    >> _limiting_memory
    >> _prepare_messages
    >> _pre_runner
    >> _run_strategy
    >> (
        GOTO(BuiltinName.STRATEGY_EOF)
        >> ALIAS(_agent_entry, BuiltinName.AGENT_STRATEGY)
        >> WHILE(_single_strategy_exec).ACTION(_advance_ctr)
        >> _strategy_post
        >> ALIAS(NOP, BuiltinName.STRATEGY_EOF)
    )
    >> _call_completion
    >> _post_runner
    >> _commit_memory
)
_workflow_rendered = _workflow.render()
