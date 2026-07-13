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
from amrita_sense.hook.matcher import MatcherFactory as MatcherManager
from amrita_sense.instructions import GOTO
from amrita_sense.instructions.subprogram import SubprogramStorage
from amrita_sense.logging import logger
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
from amrita_core.components.llm import JINJA2_RENDER, LLM_COMPLETION
from amrita_core.components.process import BUILD_MESSAGE, COMMIT_MEMORY, LOAD_STATE
from amrita_core.components.react import (
    AGENT_ENTRY,
    AGENT_POST_PROCESS,
    REACT_COUNTER,
    SINGLE_STRATEGY_CALL,
)
from amrita_core.config import AmritaConfig, get_config
from amrita_core.consts import DEFAULT_TEMPLATE
from amrita_core.contents import MessageContent
from amrita_core.contexts import (
    AbilityContext,
    AbilityState,
    AgentLoopState,
    DatabackendOptions,
    GeneralInput,
    MemoryContext,
    RespState,
    SessionMetadata,
    StateContext,
    StrategyPayload,
    WorkingState,
)
from amrita_core.hook.event import CompletionEvent, PreCompletionEvent
from amrita_core.libchat import RESPONSE_TYPE
from amrita_core.types import (
    USER_INPUT,
    Message,
    ModelPreset,
    SendMessageWrap,
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


class ChatObject:
    """Chat processing object - The minimal unit of chat processing.

    This class is responsible for processing a single chat session, including message receiving,
    context management, model calling, and response sending.
    """

    # Identity
    _s_id: str  # Temporary session ID if assigned `session_id`

    # Timing
    end_at: datetime | None
    last_call: datetime  # Last internal function call time
    now_calling: str | None  # currently calling function name

    # IO-Stream
    io_stream: SuspendObjectStream[RESPONSE_TYPE]

    # Runtime State
    _is_running: bool  # Whether it is running
    _is_done: bool  # Whether it has completed
    _task: Task[None]  # (lateinit) set on runtime
    _err: BaseException | None  # Exception in runtime

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

    # ChatObject temp storage
    _chatman: ChatManager
    _state: StateContext | None  # Backref for external consumers

    # DI context references — component nodes read/write these via extra_args type injection
    _di_ability: AbilityState
    _di_memory: MemoryContext
    _di_working: WorkingState
    _di_resp: RespState
    _di_input: GeneralInput
    _di_loop: AgentLoopState
    _di_agent: StrategyPayload
    _di_opt: DatabackendOptions
    _di_session: SessionMetadata
    __slots__ = (
        "_chatman",
        "_di_ability",
        "_di_agent",
        "_di_input",
        "_di_loop",
        "_di_memory",
        "_di_opt",
        "_di_resp",
        "_di_session",
        "_di_working",
        "_err",
        "_hook_args",
        "_hook_kwargs",
        "_interpreter",
        "_is_done",
        "_is_running",
        "_middleware",
        "_raised_exc",
        "_s_id",
        "_state",
        "_task",
        "_workflow",
        "end_at",
        "io_stream",
        "last_call",
        "now_calling",
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
        # Init runtime fields
        self._err = None
        self._is_done = False
        self._is_running = False
        self.now_calling = None
        self.end_at = None
        self._raised_exc = (
            exception_ignored if not __flags__.DISABLE_EXC_IGNORED else ()
        )
        self.last_call = datetime.now(utc)

        # initialize iostream
        self.io_stream = io_stream or SuspendObjectStream()

        # Validate context / session_id
        if not context and not session_id:
            raise ValueError("Either context or session_id must be provided")
        if session_id:
            if context:
                raise ValueError("Both context and session_id cannot be provided")
            self._s_id = session_id

        # Resolve locals (no longer stored directly on ChatObject)
        _stream_id = uuid4().hex
        _timestamp = get_current_datetime_timestamp()
        _time = datetime.now(utc)
        _config = config or get_config()
        _preset = preset
        _slot = backend if backend else BackendSlots(LegacyBackend(), LegacyBackend())
        _train = (
            train if isinstance(train, Message) else Message[str].model_validate(train)
        )
        _template = train_template
        _jv = jinja2_vars or {}
        if any(name in _jv for name in ("train", "self", "memory", "chatobj")):
            raise RuntimeError("Received a reserved keyword, please use another name.")
        _strategy = agent_strategy
        _bke_opt = backend_options or DatabackendOptions()

        self._chatman = chat_man or chat_manager
        # Hook args
        hook_kwargs = hook_kwargs or {}
        self._hook_kwargs = hook_kwargs
        self._hook_args = hook_args
        self._middleware = middleware

        # DI context objects — passed via extra_args for type-based injection
        self._di_session = SessionMetadata(
            stream_id=_stream_id,
            session_id=self._s_id if hasattr(self, "_s_id") else "",
            timestamp=_timestamp,
            time=_time,
        )
        self._di_ability = AbilityState(
            preset=_preset,
            config=_config,
            slot=_slot,
        )
        self._di_input = GeneralInput(
            user_input=user_input,
            train=_train,
            template=_template,
            jinja2_vars=_jv,
        )
        self._di_memory = MemoryContext()
        self._di_working = WorkingState()
        self._di_resp = RespState(
            extra_usage=UniResponseUsage(
                prompt_tokens=0, completion_tokens=0, total_tokens=0
            )
        )
        self._di_loop = AgentLoopState()
        self._di_agent = StrategyPayload(strategy=_strategy)
        self._di_opt = _bke_opt
        self._state = None
        if context:
            self._state = context
            self._di_memory.memory = context.memory
            self._di_ability.ability = context.ability
            self._di_session.session_id = context.session_id

        # Workflow system
        wkfl = None
        if archived_nodes is not None:
            wkfl = NodeCompose(*_workflow._graph) >> archived_nodes
        self._workflow = wkfl.render() if wkfl else _workflow_rendered
        self._interpreter = WorkflowInterpreter(
            self._workflow,
            self.io_stream,
            exception_ignored=exception_ignored,
            extra_args=(
                *hook_args,
                self,
                self._di_ability,
                self._di_memory,
                self._di_working,
                self._di_resp,
                self._di_input,
                self._di_loop,
                self._di_agent,
                self._di_opt,
                self._di_session,
            ),
            extra_kwargs=hook_kwargs,
        )

    #  Properties delegating to DI context

    @property
    def stream_id(self) -> str:
        return self._di_session.stream_id

    @stream_id.setter
    def stream_id(self, val: str) -> None:
        self._di_session.stream_id = val

    @property
    def timestamp(self) -> str:
        return self._di_session.timestamp

    @property
    def time(self) -> datetime:
        return self._di_session.time

    @property
    def config(self) -> AmritaConfig:
        return self._di_ability.config

    @config.setter
    def config(self, val: AmritaConfig) -> None:
        self._di_ability.config = val

    @property
    def preset(self) -> ModelPreset:
        p = self._di_ability.preset
        assert p is not None, "preset has not been loaded yet"
        return p

    @preset.setter
    def preset(self, val: ModelPreset) -> None:
        self._di_ability.preset = val

    @property
    def slot(self) -> BackendSlots:
        return self._di_ability.slot

    @property
    def strategy(self) -> type[AgentStrategy] | StrategyLikedObject:
        return self._di_agent.strategy

    @strategy.setter
    def strategy(self, val: type[AgentStrategy] | StrategyLikedObject) -> None:
        self._di_agent.strategy = val

    @property
    def state(self) -> StateContext:
        """Backward-compatible accessor. Returns the StateContext if one was
        provided, otherwise synthesises one from the DI components."""
        if self._state is not None:
            return self._state
        return StateContext(
            session_id=self._di_session.session_id,
            memory=self._di_memory.memory or MemoryModel(),
            ability=self._di_ability.ability or AbilityContext(),
        )

    @state.setter
    def state(self, val: StateContext) -> None:
        self._state = val
        self._di_memory.memory = val.memory
        self._di_ability.ability = val.ability
        self._di_session.session_id = val.session_id

    @property
    def user_input(self) -> USER_INPUT:
        return self._di_input.user_input

    @property
    def train(self) -> Message[str]:
        return self._di_input.train

    @train.setter
    def train(self, val: Message[str]) -> None:
        self._di_input.train = val

    @property
    def template(self) -> Template:
        return self._di_input.template

    @property
    def jinja2_vars(self) -> dict[str, Any]:
        return self._di_input.jinja2_vars

    @property
    def session_id(self) -> str:
        """
        Get the session ID for the workflow.
        Falls back to ``_s_id`` if DI session has not been initialized yet.
        """
        if hasattr(self, "_di_session"):
            return self._di_session.session_id
        return self._s_id

    @property
    def data(self) -> MemoryModel:
        """
        Get the memory model for the workflow
        """
        if not hasattr(self, "_di_memory") or self._di_memory.memory is None:
            raise RuntimeError("Memory not initialized")
        return self._di_memory.memory

    @data.setter
    def data(self, val: MemoryModel):
        if not hasattr(self, "_di_memory"):
            object.__setattr__(self, "_di_memory", MemoryContext())
        self._di_memory.memory = val

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
            self._di_session.stream_id = uuid4().hex
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
                await self.io_stream.set_queue_done()  # Write a EOF to the queue
                self.end_at = datetime.now(utc)
                self._chatman.running_chat_object_id2map.pop(self.stream_id, None)  # type: ignore[arg-type]
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
                f"ChatObject of {self.stream_id} is already running or done"  # type: ignore[arg-type]
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


#  Retained workflow nodes (use DI _di_xxx refs)


@Node(SuspendEnum.MEMORY)
async def _limiting_memory(chat_obj: ChatObject):
    logger.debug("Starting applying memory limitations..")
    mem_ctx = chat_obj._di_memory
    input_ctx = chat_obj._di_input
    ab = chat_obj._di_ability
    resp = chat_obj._di_resp
    if not ab.config.llm.enable_memory_abstract:
        return
    assert mem_ctx.memory is not None, "Memory must be loaded before limiting"
    async with MemoryLimiter(mem_ctx.memory, input_ctx.train, config=ab.config) as lim:
        await chat_obj.io_stream._wait_for_continue(SuspendEnum.MEMORY)
        await lim.run_enforce()

        if abs_usage := lim.usage:
            resp.extra_usage = gather_usage(resp.extra_usage, abs_usage)
        mem_ctx.memory = lim.memory
    logger.debug("Memory limitation application completed")


@Node(SuspendEnum.PRECOMPLE)
async def _pre_runner(chat_obj: ChatObject):
    wok = chat_obj._di_working
    ab = chat_obj._di_ability
    input_ctx = chat_obj._di_input
    mem_ctx = chat_obj._di_memory
    assert wok.context_wrap is not None, "Context wrap must be built before pre-runner"
    assert mem_ctx.memory is not None, "Memory must be loaded before pre-runner"
    logger.debug(
        f"Starting chat processing, sending message count: {len(wok.context_wrap)}"
    )

    logger.debug("Triggering matcher functions..")
    messages = wok.context_wrap
    chat_event = PreCompletionEvent(
        chat_object=chat_obj,
        user_input=input_ctx.user_input,
        original_context=messages,
    )
    assert ab.ability is not None, "Ability must be loaded before pre-runner"
    await MatcherManager.trigger_event(
        chat_event,
        ab.config,
        chat_obj,
        ab.preset,
        *chat_obj._hook_args,
        state=StateContext(
            session_id=chat_obj._di_session.session_id,
            memory=mem_ctx.memory,
            ability=ab.ability,
        ),
        slot=ab.slot,
        exception_ignored=chat_obj._raised_exc,
        **chat_obj._hook_kwargs,
    )
    mem_ctx.memory.messages = chat_event.get_context_messages().unwrap(
        exclude_system=True
    )


@Node(SuspendEnum.STRATEGY_START)
async def _run_strategy(chat_obj: ChatObject, intp: WorkflowInterpreter) -> None:
    """Run workflow of strategy given."""
    agent = chat_obj._di_agent
    input_ctx = chat_obj._di_input
    ab = chat_obj._di_ability
    wok = chat_obj._di_working
    assert wok.context_wrap is not None, "Context wrap must be built before strategy"

    match agent.strategy.get_category():
        case "agent-mixed" | "agent":
            context = (
                SendMessageWrap.validate_messages(
                    [
                        input_ctx.train,
                        Message(role="user", content=input_ctx.user_input),
                    ]
                )
                if ab.config.function_config.use_minimal_context
                else wok.context_wrap.copy()
            )
            ctx = StrategyContext(input_ctx.user_input, context, chat_obj)
            chat_obj._di_loop.stg_ctx = ctx
            return intp.jump_to(intp.find_addr_alias(BuiltinName.AGENT_STRATEGY))

        case "rag":
            context = SendMessageWrap.validate_messages(
                [
                    input_ctx.train,
                    Message(role="user", content=input_ctx.user_input),
                ]
            )
        case "workflow":
            context = wok.context_wrap.copy()
        case _:
            raise RuntimeError("Invalid agent strategy")
    ctx = StrategyContext(input_ctx.user_input, context, chat_obj)
    st = agent.strategy(ctx)
    try:
        await st.run()
    except Exception as e:
        if isinstance(e, chat_obj._raised_exc):
            raise
        with contextlib.suppress(NoExceptionHandler):
            await st.on_exception(e)
    else:
        await st.on_post_process()
    wok.context_wrap.extend(ctx.original_context.end_messages)


@Node(SuspendEnum.COMPLE)
async def _post_runner(chat_obj: ChatObject):
    wok = chat_obj._di_working
    ab = chat_obj._di_ability
    input_ctx = chat_obj._di_input
    mem_ctx = chat_obj._di_memory
    resp = chat_obj._di_resp
    assert wok.context_wrap is not None, "Context wrap must be set before post-runner"
    assert resp.response is not None, "Response must be set before post-runner"
    assert mem_ctx.memory is not None, "Memory must be loaded before post-runner"
    assert ab.ability is not None, "Ability must be loaded before post-runner"
    logger.debug("Triggering chat events..")
    chat_event = CompletionEvent(
        input_ctx.user_input,
        wok.context_wrap,
        chat_obj,
        resp.response.content,
    )
    await chat_obj.io_stream._wait_for_continue(SuspendEnum.COMPLE)
    await MatcherManager.trigger_event(
        chat_event,
        ab.config,
        chat_obj,
        ab.preset,
        *chat_obj._hook_args,
        state=StateContext(
            session_id=chat_obj._di_session.session_id,
            memory=mem_ctx.memory,
            ability=ab.ability,
        ),
        slot=ab.slot,
        exception_ignored=chat_obj._raised_exc,
        **chat_obj._hook_kwargs,
    )
    resp.response.content = chat_event.model_response
    wok.context_wrap.append(
        Message[str](
            content=resp.response.content,
            role="assistant",
        )
    )
    logger.debug(
        f"Added assistant response to memory, current message count: {len(wok.context_wrap)}"
    )
    assert wok.context_wrap is not None
    mem_ctx.memory.messages = wok.context_wrap.unwrap(True)
    logger.debug("Chat processing completed")


# pre-compile workflows — component nodes + retained local nodes
_single_call = SINGLE_STRATEGY_CALL(fallback_on_fail=False)
_workflow: NodeCompose = (
    LOAD_STATE
    >> JINJA2_RENDER
    >> _limiting_memory
    >> BUILD_MESSAGE
    >> _pre_runner
    >> _run_strategy
    >> (
        GOTO(BuiltinName.STRATEGY_EOF)
        >> ALIAS(AGENT_ENTRY, BuiltinName.AGENT_STRATEGY)
        >> WHILE(_single_call).ACTION(REACT_COUNTER)
        >> AGENT_POST_PROCESS
        >> ALIAS(NOP, BuiltinName.STRATEGY_EOF)
    )
    >> LLM_COMPLETION
    >> _post_runner
    >> COMMIT_MEMORY
)
_workflow_rendered = _workflow.render()
