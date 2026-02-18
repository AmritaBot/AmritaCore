import inspect
from collections.abc import Awaitable, Callable
from copy import deepcopy
from types import FrameType
from typing import (
    Any,
    ClassVar,
    TypeAlias,
)

from pydantic import BaseModel, Field
from typing_extensions import Self

from amrita_core.config import AmritaConfig
from amrita_core.logging import debug_log, logger

from .event import Event
from .exception import BlockException, CancelException, PassException

ChatException: TypeAlias = BlockException | CancelException | PassException


class FunctionData(BaseModel, arbitrary_types_allowed=True):
    function: Callable[..., Awaitable[Any]] = Field(...)
    signature: inspect.Signature = Field(...)
    frame: FrameType = Field(...)
    priority: int = Field(...)
    block: bool = Field(...)
    matcher: Any = Field(...)


class EventRegistry:
    _instance = None
    __event_handlers: ClassVar[dict[str, list[FunctionData]]] = {}

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register_handler(self, event_type: str, data: FunctionData):
        self.__event_handlers.setdefault(event_type, []).append(data)

    def get_handlers(self, event_type: str) -> list[FunctionData]:
        self.__event_handlers.setdefault(event_type, [])
        self.__event_handlers[event_type].sort(key=lambda x: x.priority, reverse=False)
        return self.__event_handlers[event_type]

    def _all(self) -> dict[str, list[FunctionData]]:
        return self.__event_handlers


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
            block=self.block,
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

    def stop_process(self):
        """
        Stop the current matcher then break the matcher loop.
        """
        raise BlockException()

    def cancel_matcher(self):
        """
        Stop the matcher then cancel the matcher loop.
        """
        raise CancelException()

    def pass_event(self):
        """
        Ignore the current handler and continue processing the next one.
        """
        raise PassException()


class MatcherManager:
    """
    Event handling manager.
    """

    @staticmethod
    async def trigger_event(
        event: Event | None = None, config: AmritaConfig | None = None, *args, **kwargs
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
            if isinstance(i, Event):
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
        event_type = event.get_event_type()  # Get event type
        priority_tmp = 0
        debug_log(f"Running matchers for event: {event_type}!")
        # Check if there are handlers for this event type
        if matcher_list := EventRegistry().get_handlers(event_type):
            for matcher in matcher_list:
                if matcher.priority != priority_tmp:
                    priority_tmp = matcher.priority
                    debug_log(f"Running matchers for priority {priority_tmp}......")

                signature = matcher.signature
                frame = matcher.frame
                line_number = frame.f_lineno
                file_name = frame.f_code.co_filename
                handler = matcher.function
                session_args = (matcher.matcher, event, config, *args)
                session_kwargs = {**deepcopy(kwargs)}

                args_types = {k: v.annotation for k, v in signature.parameters.items()}
                filtered_args_types = {
                    k: v for k, v in args_types.items() if v is not inspect._empty
                }
                if args_types != filtered_args_types:
                    failed_args = list(args_types.keys() - filtered_args_types.keys())
                    logger.warning(
                        f"Matcher {matcher.function.__name__} (File: {file_name}: Line {frame.f_lineno!s}) has untyped parameters!"
                        + f"(Args:{''.join(i + ',' for i in failed_args)}).Skipping......"
                    )
                    continue
                new_args = []
                used_indices = set()
                for param_type in filtered_args_types.values():
                    for i, arg in enumerate(session_args):
                        if i in used_indices:
                            continue
                        if isinstance(arg, param_type):
                            new_args.append(arg)
                            used_indices.add(i)
                            break

                # Get keyword argument type annotations
                kwparams = signature.parameters
                f_kwargs = {  # TODO: kwparams dependent support
                    param_name: session_kwargs[param.annotation]
                    for param_name, param in kwparams.items()
                    if param.annotation in session_kwargs
                }
                if len(new_args) != len(list(filtered_args_types)):
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
                except CancelException:
                    logger.info("Cancelled Matcher processing")
                    return
                except BlockException:
                    break
                except Exception as e:
                    if exception_ignored and isinstance(e, exception_ignored):
                        raise
                    logger.opt(exception=e, colors=True).error(
                        f"An error occurred while running '{handler.__name__}'({file_name}:{line_number}) "
                    )

                    continue
                finally:
                    logger.info(f"Handler {handler.__name__} finished")
                    if matcher.block:
                        break
        else:
            logger.warning(
                f"No registered Matcher for {event_type} event, skipping processing."
            )
