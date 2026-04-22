import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from functools import wraps
from typing import Any, Generic, TypeAlias, TypeVar

import aiologic
import anyio
from anyio.abc import ObjectReceiveStream, ObjectSendStream
from typing_extensions import LiteralString

ObjectTypeT = TypeVar("ObjectTypeT")
CALLBACK_TYPE: TypeAlias = Callable[[ObjectTypeT], Awaitable[Any]]
SUSPEND_ON_YIELD: LiteralString = "SuspendObjectStream::yield_response"


class SuspendObjectStream(Generic[ObjectTypeT]):
    """
    A class for objects that can be suspended and resumed.

    This implements a producer-to-single-consumer architecture, where one producer
    can send items to exactly one consumer through an asynchronous stream.
    """

    __done_marker = object()

    # Suspension-related attributes
    __suspend_signal: asyncio.Future | None = None
    __resume_signal: asyncio.Future | None = None
    _suspend_tags: tuple[str, ...] | None = None

    # Callback-related attributes
    _callback_fun: CALLBACK_TYPE | None = None
    _callback_lock: aiologic.Lock

    # Stream-related attributes
    _send_stream: ObjectSendStream
    _receive_stream: ObjectReceiveStream

    # Queue state attributes
    _queue_done: bool = False
    _has_consumer: bool = False
    _q_tout: float | None

    def __init__(
        self,
        /,
        queue_size: int = 45,
        queue_timeout: float | None = 10.0,
        callback: CALLBACK_TYPE | None = None,
    ) -> None:
        self._send_stream, self._receive_stream = anyio.create_memory_object_stream(
            max_buffer_size=queue_size
        )
        self._callback_fun = callback
        self._callback_lock = aiologic.Lock()
        self._q_tout = queue_timeout

    @staticmethod
    def suspend(func: Callable[..., Any], tag: str | None = None) -> Callable[..., Any]:
        """Decorator for suspend. (Only be used for a time-costly function)"""
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"{func.__name__} is not a coroutine function.")

        @wraps(func)
        async def wrapper(*args, **kwargs):
            chat_object = None
            for arg in args:
                if isinstance(arg, SuspendObjectStream):
                    chat_object = arg
                    break
            if chat_object is None:
                for value in kwargs.values():
                    if isinstance(value, SuspendObjectStream):
                        chat_object = value
                        break
            if chat_object is None:
                raise TypeError(
                    f"No SuspendObjectStream parameter found in function '{func.__name__}'. "
                    f"Args types: {[type(a).__name__ for a in args]}, "
                    f"Kwargs keys: {list(kwargs.keys())}"
                )

            await chat_object._wait_for_continue(tag)
            return await func(*args, **kwargs)

        return wrapper

    @staticmethod
    def suspend_with_tag(tag: str):
        """Decorator for suspend with tag filter. Used in inner function.

        Args:
            tag (str): Tag for break point.
        """

        return lambda func: SuspendObjectStream.suspend(func, tag)

    async def _wait_for_continue(self, tag: str | None = None) -> bool:
        """Break point for suspend.

        Args:
            tag (str | None): Tag for break point.

        Returns:
            bool: True if has really waited during running, False if not.
        """
        if self.__suspend_signal is None:
            return False
        elif (
            self._suspend_tags
        ):  # When tags filter exists, only suspend when tag matches
            if tag is None or tag not in self._suspend_tags:
                return False
        await asyncio.sleep(0)
        if self.__resume_signal is not None and not self.__resume_signal.done():
            await self.__resume_signal
            return True
        try:
            self.__suspend_signal.set_result(True)
            self.__resume_signal = asyncio.Future()
            await self.__resume_signal
            return True
        finally:
            self.__resume_signal = None

    async def wait_to_suspend(self, *tags: str, timeout: float | None = None):  # noqa: ASYNC109
        """Tell SuspendObjectStream to suspend and wait for it.

        Args:
            *tags (str): Tags to wait for (filter break points).
            timeout (float | None, optional): Timeout for waiting. Defaults to None.

        Raises:
            RuntimeError: Raised when already waiting.
        """
        if self.__suspend_signal is not None:
            if self.__suspend_signal.done():
                self.__suspend_signal = None
            else:
                raise RuntimeError("Already waiting for suspend!")
        try:
            self._suspend_tags = tags
            self.__suspend_signal = asyncio.Future()
            await asyncio.wait_for(self.__suspend_signal, timeout)
        finally:
            self.__suspend_signal = None
            self._suspend_tags = None

    def resume(self) -> None:
        """Resume to run when suspend."""
        if self.__resume_signal and not self.__resume_signal.done():
            self.__resume_signal.set_result(True)
            self._suspend_tags = None

    def queue_closed(self) -> bool:
        """Check if the response queue is closed.

        Returns:
            bool: True if the queue is closed, False otherwise.
        """
        return self._queue_done

    async def set_queue_done(self) -> None:
        """Mark the response queue as done by putting the done marker."""
        if not self.queue_closed():
            try:
                await self._put_to_queue(self.__done_marker)
            except anyio.BrokenResourceError:
                self._queue_done = True
            else:
                self._queue_done = True

    async def _put_to_queue(self, item):
        """Put an item to the queue, using overflow mechanism if primary queue is full.

        Args:
            item: Item to put in the queue.
        """
        with anyio.fail_after(self._q_tout):
            await self._send_stream.send(item)

    async def yield_response(self, response: ObjectTypeT) -> None:
        """Send chat model response to the queue allowing both str and MessageContent types.

        Args:
            response: Either a string or MessageContent object to be sent to the queue.
        """
        await self._wait_for_continue(SUSPEND_ON_YIELD)
        if self._callback_fun is not None:
            async with self._callback_lock:
                await self._callback_fun(response)
        else:
            if not self.queue_closed():
                await self._put_to_queue(response)
            else:
                raise RuntimeError("Queue is closed.")

    def set_callback_func(self, func: CALLBACK_TYPE) -> None:
        """Set a callback function to be executed when a response is yielded.

        Args:
            func (CALLBACK_TYPE): Function to be executed when a response is yielded.

        Raises:
            RuntimeError: If a callback function is already set.
        """
        if not self._callback_fun:
            self._callback_fun = func
        else:
            raise RuntimeError(
                "The callback function of this chat object has already been set!"
            )

    async def yield_response_iteration(
        self, iterator: AsyncGenerator[ObjectTypeT, None]
    ):
        """Send chat model response to the queue allowing both str and MessageContent types.

        Args:
            iterator: An async generator that yields either strings or MessageContent objects.
        """
        async for chunk in iterator:
            await self.yield_response(chunk)

    def get_response_generator(self) -> AsyncGenerator[ObjectTypeT, None]:
        """Return an async generator to iterate over responses from the queue.

        Yields:
            ObjectTypeT: Either a string or MessageContent object from the response queue.

        Raises:
            RuntimeError: If response is already being consumed.
        """
        if self._has_consumer or self._callback_fun is not None:
            raise RuntimeError("Response is already being consumed.")
        self._has_consumer = True
        return self._response_generator()

    async def _response_generator(self) -> AsyncGenerator[ObjectTypeT]:
        """Internal method to asynchronously yield items from the queue until done marker is reached.

        Yields:
            ObjectTypeT: Items from the response queue until the done marker is encountered.
        """
        try:
            async for item in self._receive_stream:
                if item is self.__done_marker:
                    return
                yield item
        finally:
            self._queue_done = True
            await self._send_stream.aclose()
