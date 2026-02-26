from __future__ import annotations

import asyncio
import inspect
import warnings
from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from copy import deepcopy
from types import FrameType, MappingProxyType
from typing import (
    Any,
    ClassVar,
    Generic,
    TypeAlias,
    TypeVar,
    overload,
)

from deprecated.sphinx import deprecated
from exceptiongroup import ExceptionGroup
from pydantic import BaseModel, Field
from typing_extensions import Self

from amrita_core.config import AmritaConfig
from amrita_core.hook.event import EventTypeEnum
from amrita_core.logging import debug_log, logger

from .event import BaseEvent
from .exception import (
    BlockException,
    CancelException,
    MatcherException,
    PassException,
)

ChatException: TypeAlias = MatcherException


class FunctionData(BaseModel, arbitrary_types_allowed=True):
    function: Callable[..., Awaitable[Any]] = Field(...)
    signature: inspect.Signature = Field(...)
    frame: FrameType = Field(...)
    priority: int = Field(...)
    matcher: Matcher = Field(...)


class EventRegistry:
    _instance = None
    _event_handlers: ClassVar[
        defaultdict[str, defaultdict[int, list[FunctionData]]]
    ] = defaultdict(lambda: defaultdict(list))

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register_handler(self, event_type: str, data: FunctionData):
        self._event_handlers[event_type][data.priority].append(data)

    def get_handlers(self, event_type: str) -> defaultdict[int, list[FunctionData]]:
        return self._event_handlers[event_type]

    @deprecated(reason="Use `get_all()` instead.", version="0.6.0")
    def _all(self) -> defaultdict[str, defaultdict[int, list[FunctionData]]]:
        return self.get_all()

    def get_all(self) -> defaultdict[str, defaultdict[int, list[FunctionData]]]:
        return self._event_handlers


class Matcher:
    def __init__(self, event_type: str, priority: int = 10, block: bool = True):
        """Constructor, initialize Matcher object.
        Args:
            event_type (str): Event type
            priority (int, optional): Priority. Defaults to 10.
            block (bool, optional): Whether to block subsequent events. Defaults to True.
        """
        if priority <= 0:
            raise ValueError("Event priority cannot be zero or negative!")

        self.event_type = event_type
        self.priority = priority
        self.block = block

    def append_handler(self, func: Callable[..., Awaitable[Any]]):
        frame = inspect.currentframe()
        assert frame is not None, "Frame is None!!!"
        func_data = FunctionData(
            function=func,
            signature=inspect.signature(func),
            frame=frame,
            priority=self.priority,
            matcher=self,
        )
        EventRegistry().register_handler(self.event_type, func_data)

    def handle(self):
        """
        Event handler registration function
        """

        def wrapper(
            func: Callable[..., Awaitable[Any]],
        ):
            self.append_handler(func)
            return func

        return wrapper

    def set_block(self, block: bool):
        self.block = block

    def stop_process(self):
        """
        Stop the current matcher then break the matcher loop.
        """
        raise CancelException()

    @deprecated(reason="Use `stop_process()` instead.", version="0.6.0")
    def cancel_matcher(self):
        """
        Stop the matcher then cancel the matcher loop.
        """
        warnings.warn(
            "This method is deprecated, please `use stop_process()` instead.",
            category=DeprecationWarning,
        )
        self.stop_process()

    def pass_event(self):
        """
        Ignore the current handler and continue processing the next one.
        """
        raise PassException()


T = TypeVar("T")


class DependsFactory(Generic[T]):
    """
    Dependency factory class.
    """

    _depency_func: Callable[..., T | Awaitable[T]]

    def __init__(self, depency: Callable[..., T | Awaitable[T]]):
        self._depency_func = depency

    async def resolve(self, *args, **kwargs) -> T | None:
        """
        Resolve dependencies for a function.

        Args:
            *args: Positional arguments for dependency injection
            **kwargs: Keyword arguments for dependency injection

        Returns:
            T: The resolved dependency
        """
        success, args, kwargs, dkw = MatcherFactory._resolve_dependencies(
            inspect.signature(self._depency_func),
            session_args=args,
            session_kwargs=kwargs,
        )
        if dkw:
            raise RuntimeError(
                "As a resolver function, using `Depends` in dependency injection factory is disallowed."
            )
        if not success:
            return None
        rs: T | Awaitable[T] = self._depency_func(*args, **kwargs)
        if isinstance(rs, Awaitable):
            rs = await rs
        return rs


def Depends(dependency: Callable[..., T | Awaitable[T]]) -> Any:
    """
    Dependency injection decorator.

    Args:
        dependency: The dependency function to inject

    Returns:
        DependsFactory: A factory for dependency injection

    Example:
        ```python
        async def get_example_dependency(...) -> Any | None:
            ...

        @on_precompletion()
        async def a_function_with_dependencies(
            event: PreCompletionEvent,
            dep: ExampleDependency = Depends(get_example_dependency),
        ):
            ...
        ```

        If DependendsFactory's return is None, this function won't be called.
    """
    return DependsFactory[T](dependency)


class MatcherFactory:
    """
    Event handling factory class.
    """

    @staticmethod
    def _resolve_dependencies(
        signature: inspect.Signature,
        session_args: Iterable[Any],
        session_kwargs: dict[str, Any],
    ) -> tuple[bool, tuple, dict[str, Any], dict[str, DependsFactory]]:
        """
        Resolve dependencies for a function based on its signature and available arguments.

        Args:
            signature: Function signature to resolve dependencies for
            session_args: Available positional arguments for dependency injection
            session_kwargs: Available keyword arguments for dependency injection

        Returns:
            tuple[bool, tuple, dict]: A tuple containing:
                - bool: Whether dependency resolution was successful
                - tuple: Resolved positional arguments
                - dict: Resolved keyword arguments
                - dict: kwargs should be resolved by dependency injection
        """
        args_types = {k: v.annotation for k, v in signature.parameters.items()}
        filtered_args_types = {
            k: v for k, v in args_types.items() if v is not inspect._empty
        }

        # Check if all parameters are typed
        if args_types != filtered_args_types:
            return False, (), {}, {}

        new_args = []
        used_indices: set[int] = set()
        param_names_resolved: set[str] = set()
        required_params: dict[str, inspect.Parameter] = {
            name: param
            for name, param in signature.parameters.items()
            if param.default == inspect.Parameter.empty
        }
        for name, param in required_params.items():
            param_type: type[Any] = param.annotation
            found = False
            if name in session_kwargs:
                param_names_resolved.add(name)
                found = True
            else:
                # Look for positional argument match
                for i, arg in enumerate(session_args):
                    if i in used_indices:
                        continue
                    if isinstance(arg, param_type):
                        new_args.append(arg)
                        used_indices.add(i)
                        param_names_resolved.add(name)
                        found = True
                        break
            if not found:
                return False, (), {}, {}

        # Get keyword arguments from session_kwargs that match function signature
        kwparams: MappingProxyType[str, inspect.Parameter] = signature.parameters
        f_kwargs: dict[str, Any] = {
            param_name: session_kwargs[param_name]
            for param_name in kwparams.keys()
            if param_name in session_kwargs
        }

        # Get default dependencies from function signature
        d_kwargs: dict[str, DependsFactory] = {
            k: v.default
            for k, v in kwparams.items()
            if isinstance(v.default, DependsFactory)
        }

        # Verify all required parameters are resolved
        if len(param_names_resolved) != len(required_params):
            return False, (), {}, {}

        return True, tuple(new_args), f_kwargs, d_kwargs

    @staticmethod
    async def _do_runtime_resolve(
        runtime_args: dict[int, DependsFactory],
        runtime_kwargs: dict[str, DependsFactory],
        args2update: list[Any],
        kwargs2update: dict[str, Any],
        session_args: list[Any],
        session_kwargs: dict[str, Any],
        exception_ignored: tuple[type[BaseException], ...],
    ) -> bool:
        """Do a runtime resolve of dependencies.

        Args:
            runtime_args (dict[int, DependsFactory]): This is a dict of args dependencies (usually be passed in `trigger_event`) to resolve.
            runtime_kwargs (dict[str, DependsFactory]): This is a dict of kwargs dependencies to resolve.
            args2update (list[Any]): This is a list of args to update.
            kwargs2update (dict[str, Any]): This is a dict of kwargs to update.
            session_args (list[Any]): This is a list of args that can be used from the session .
            session_kwargs (dict[str, Any]): This is a dict of kwargs that can be used from the session.
            exception_ignored (tuple[type[BaseException], ...]): These exception will be raised again if occurred.

        Raises:
            result: if these exception

        Returns:
            result (bool): Return True if all injections are resolved, otherwise returns False
        """
        resolve_tasks = []
        if not runtime_args and not runtime_kwargs:
            return True
        session_args = deepcopy(session_args)
        session_kwargs = deepcopy(session_kwargs)
        for idx, factory in runtime_args.items():
            task = factory.resolve(*session_args, **session_kwargs)
            resolve_tasks.append((idx, None, task))
        for key, factory in runtime_kwargs.items():
            task = factory.resolve(*session_args, **session_kwargs)
            resolve_tasks.append((None, key, task))
        resolved_results: list[Any | BaseException] = await asyncio.gather(
            *[task for _, _, task in resolve_tasks], return_exceptions=True
        )
        excs = []
        args_tmp: dict[int, Any] = {}
        kwargs_tmp: dict[str, Any] = {}
        for (idx, key, _), result in zip(resolve_tasks, resolved_results):
            if isinstance(result, BaseException):
                if isinstance(result, exception_ignored):
                    raise result
                excs.append(result)
            elif result is None:
                return False
            else:
                if idx is not None:
                    args_tmp[idx] = result
                elif key is not None:
                    kwargs_tmp[key] = result
        if excs:
            raise ExceptionGroup("Some exceptions had occurred.", excs)
        del resolved_results
        for k, v in args_tmp.items():
            args2update[k] = v
        del args_tmp
        kwargs2update.update(kwargs_tmp)
        return True

    @classmethod
    async def _simple_run(
        cls,
        matcher_list: list[FunctionData],
        event: BaseEvent,
        config: AmritaConfig,
        exception_ignored: tuple[type[BaseException], ...],
        extra_args: tuple,
        extra_kwargs: dict[str, Any],
    ) -> bool:
        """Run a round of matcher

        Args:
            matcher_list (list[FunctionData]): Matchers to run
            event (BaseEvent): event
            config (AmritaConfig): Config
            exception_ignored (tuple[type[BaseException], ...]): Exceptions to ignore(to raise again)
            extra_args (tuple): extra args for dependency injection
            extra_kwargs (dict[str, Any]): extra kwargs for dependency injection

        Returns:
            bool: Should continue to run.
        """
        for func in matcher_list:
            signature = func.signature
            frame = func.frame
            line_number = frame.f_lineno
            file_name = frame.f_code.co_filename
            handler = func.function
            session_args = [func.matcher, event, config, *extra_args]
            session_kwargs: dict[str, Any] = deepcopy(extra_kwargs)
            runtime_args: dict[int, DependsFactory] = {  # index -> DependsFactory
                k: v
                for k, v in enumerate(session_args)
                if isinstance(v, DependsFactory)
            }
            runtime_kwargs = {
                k: v for k, v in session_kwargs.items() if isinstance(v, DependsFactory)
            }
            # These args/kwargs will be generated by Depends
            if runtime_args or runtime_kwargs:
                if not await cls._do_runtime_resolve(
                    runtime_args,
                    runtime_kwargs,
                    session_args,
                    session_kwargs,
                    session_args,
                    session_kwargs,
                    exception_ignored,
                ):
                    raise RuntimeError("Runtime arguments cannot be resolved")

            success, new_args, f_kwargs, d_kw = MatcherFactory._resolve_dependencies(
                signature, session_args, session_kwargs
            )
            if not success:
                failed_args = list(
                    {
                        k: v
                        for k, v in signature.parameters.items()
                        if v.annotation is inspect._empty
                    }.keys()
                )
                if failed_args:
                    logger.warning(
                        f"Matcher {func.function.__name__} (File: {file_name}: Line {frame.f_lineno!s}) has untyped parameters!"
                        + f"(Args:{''.join(i + ',' for i in failed_args)}).Skipping......"
                    )
                continue
            # Do kwargs dependency injection
            if d_kw and not await cls._do_runtime_resolve(
                {},
                d_kw,
                [],
                f_kwargs,
                session_args,
                session_kwargs,
                exception_ignored,
            ):
                continue

            # Call the handler
            try:
                logger.info(f"Starting to run Matcher: '{handler.__name__}'")

                await handler(*new_args, **f_kwargs)
            except PassException:
                logger.info(
                    f"Matcher '{handler.__name__}'(~{file_name}:{line_number}) was skipped"
                )
                continue
            except Exception as e:
                if isinstance(e, CancelException | BlockException):
                    logger.info("Cancelled Matcher processing")
                    return False
                elif isinstance(e, ChatException):
                    raise
                elif exception_ignored and isinstance(e, exception_ignored):
                    raise
                logger.opt(exception=e, colors=True).error(
                    f"An error occurred while running '{handler.__name__}'({file_name}:{line_number}) "
                )
                continue
            finally:
                logger.info(f"Handler {handler.__name__} finished")
                if func.matcher.block:
                    return False
        return True

    @overload
    @classmethod
    async def trigger_event(
        cls,
        event: BaseEvent,
        config: AmritaConfig,
        /,
        exception_ignored: tuple[type[Exception], ...] = (),
    ) -> None: ...

    @overload
    @classmethod
    async def trigger_event(
        cls,
        event: BaseEvent,
        config: AmritaConfig,
        **kwargs: Any,
    ) -> None: ...

    @overload
    @classmethod
    async def trigger_event(
        cls,
        event: BaseEvent,
        config: AmritaConfig,
        *args: Any,
    ) -> None: ...
    @overload
    @classmethod
    async def trigger_event(
        cls,
        event: BaseEvent,
        config: AmritaConfig,
        *args: Any,
        exception_ignored: tuple[type[Exception], ...] = (),
    ) -> None: ...
    @overload
    @classmethod
    async def trigger_event(
        cls,
        event: BaseEvent,
        config: AmritaConfig,
        *args: Any,
        exception_ignored: tuple[type[Exception], ...] = (),
        **kwargs: Any,
    ) -> None: ...
    @overload
    @classmethod
    async def trigger_event(
        cls,
        event: BaseEvent,
        config: AmritaConfig,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
    @classmethod
    async def trigger_event(
        cls,
        event: BaseEvent,
        config: AmritaConfig,
        *args: Any,
        exception_ignored: tuple[type[Exception], ...] = (),
        **kwargs,
    ) -> None:
        """Trigger a specific type of event and call all registered event handlers for that type.

        Args:
            event (BaseEvent): Event which will be used for DI system
            config (AmritaConfig): Configh which will be used for DI
            *args (Any): Positional arguments for DI
            exception_ignored (tuple[type[Exception], ...], optional): Exceptions that will be raised again if occurred. Defaults to tuple().
            **kwargs (Any): Keyword arguments for DI

        Raises:
            RuntimeError: If event or config is None, it will raise RuntimeError.
        """
        for i in args:
            if isinstance(i, BaseEvent):
                event = i
            elif isinstance(i, AmritaConfig):
                config = i
        if not event:
            raise RuntimeError("No event found in args")
        elif not config:
            raise RuntimeError("No config found in args")

        session_kwargs = kwargs
        event_type: EventTypeEnum | str = event.get_event_type()  # Get event type
        handlers = EventRegistry().get_handlers(event_type)
        priorities: list[int] = sorted(handlers.keys(), reverse=False)
        debug_log(f"Running matchers for event: {event_type}!")
        # Check if there are handlers for this event type
        if priorities:
            for priority in priorities:
                logger.info(f"Running matchers for priority {priority}......")
                if not await cls._simple_run(
                    handlers[priority],
                    event,
                    config,
                    exception_ignored,
                    args,
                    session_kwargs,
                ):
                    break
        else:
            logger.warning(
                f"No registered Matcher for {event_type} event, skipping processing."
            )


MatcherManager = MatcherFactory
