from __future__ import annotations

import inspect
import warnings
from collections import defaultdict
from collections.abc import Awaitable, Callable
from copy import deepcopy
from types import FrameType
from typing import (
    Any,
    ClassVar,
    TypeAlias,
)

from deprecated.sphinx import deprecated
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


class MatcherFactory:
    """
    Event handling factory class.
    """

    @staticmethod
    def _resolve_dependencies(
        signature: inspect.Signature,
        session_args: tuple,
        session_kwargs: dict[str, Any],
    ) -> tuple[bool, tuple, dict[str, Any]]:
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
        """
        args_types = {k: v.annotation for k, v in signature.parameters.items()}
        filtered_args_types = {
            k: v for k, v in args_types.items() if v is not inspect._empty
        }

        # Check if all parameters are typed
        if args_types != filtered_args_types:
            return False, (), {}

        new_args = []
        used_indices = set()
        for param_type in filtered_args_types.values():
            found = False
            for i, arg in enumerate(session_args):
                if i in used_indices:
                    continue
                if isinstance(arg, param_type):
                    new_args.append(arg)
                    used_indices.add(i)
                    found = True
                    break
            if not found:
                return False, (), {}

        # Get keyword argument type annotations
        kwparams = signature.parameters
        f_kwargs = {
            param_name: session_kwargs[param.annotation]
            for param_name, param in kwparams.items()
            if param.annotation in session_kwargs
        }

        # Verify all required positional arguments are resolved
        if len(new_args) != len(list(filtered_args_types)):
            return False, (), {}

        return True, tuple(new_args), f_kwargs

    @staticmethod
    async def _simple_run(
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
            session_args = (func.matcher, event, config, *extra_args)
            session_kwargs = {**deepcopy(extra_kwargs)}

            # Use the new resolve_dependencies helper function
            success, new_args, f_kwargs = MatcherFactory._resolve_dependencies(
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

            # Call the handler
            try:
                logger.info(f"Starting to run Matcher: '{handler.__name__}'")

                await handler(*new_args, **f_kwargs)
            except PassException:
                logger.info(
                    f"Matcher '{handler.__name__}'(~{file_name}:{line_number}) was skipped"
                )
                continue
            except CancelException | BlockException:
                logger.info("Cancelled Matcher processing")
                return False
            except Exception as e:
                if exception_ignored and isinstance(e, exception_ignored):
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

    @classmethod
    async def trigger_event(
        cls,
        event: BaseEvent | None = None,
        config: AmritaConfig | None = None,
        *args,
        **kwargs,
    ) -> None:
        """
        Trigger a specific type of event and call all registered event handlers for that type.

        Parameters:
        - event: Event object containing event-related data.
        - config: Configuration object.
        - exception_ignored: Tuple of exceptions to ignore (they won't be catching when occurs).
        - *args: Variable arguments passed to the dependency injection system.
        - **kwargs: Keyword arguments passed to the dependency injection system.
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
        exception_ignored: tuple[type[BaseException], ...] = kwargs.pop(
            "exception_ignored", ()
        )
        event_type: EventTypeEnum | str = event.get_event_type()  # Get event type
        handlers = EventRegistry().get_handlers(event_type)
        priorities: list[int] = sorted(handlers.keys(), reverse=False)
        debug_log(f"Running matchers for event: {event_type}!")
        # Check if there are handlers for this event type
        if priorities:
            for priority in priorities:
                logger.info(f"Running matchers for priority {priority}......")
                if not await cls._simple_run(
                    handlers[priority], event, config, exception_ignored, args, kwargs
                ):
                    break
        else:
            logger.warning(
                f"No registered Matcher for {event_type} event, skipping processing."
            )


MatcherManger = MatcherFactory
