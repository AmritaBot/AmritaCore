from __future__ import annotations

import typing
from collections.abc import AsyncGenerator, Callable, Generator, Sequence
from io import StringIO

from amrita_sense.logging import debug_log
from amrita_sense.streaming import SuspendObjectStream
from pydantic import ValidationError

from amrita_core.base.adapter import (
    COMPLETION_RETURNING,
    AdapterManager,
    MessageContent,
    ModelAdapter,
)
from amrita_core.preset import PresetManager

from .config import AmritaConfig, get_config
from .tokenizer import hybrid_token_count
from .tools.models import ToolChoice
from .types import (
    CONTENT_LIST_TYPE,
    CONTENT_LIST_TYPE_ITEM,
    EmbeddingChunk,
    Message,
    ModelPreset,
    ThinkingConfig,
    ToolCall,
    ToolResult,
    UniResponse,
    UniResponseUsage,
)

T = typing.TypeVar("T")

RESPONSE_TYPE: typing.TypeAlias = str | MessageContent


def text_generator(
    memory: CONTENT_LIST_TYPE, split_role: bool = False, full_message: bool = False
) -> Generator[str, None, str]:
    """Generator that yields text content from a list of messages.

    Args:
        memory: List of message objects containing content
        split_role: Whether to prepend role-specific prefixes to content
        full_message: Whether to include full message content in the output

    Yields:
        Individual text strings from the message content
    """
    memory_l = [(i.model_dump() if hasattr(i, "model_dump") else i) for i in memory]
    role_map = {
        "assistant": "<BOT's response>",
        "user": "<User's query>",
        "tool": "<Tool call>",
    }
    for st in memory_l:
        if st["content"] is None:
            continue
        if isinstance(st["content"], str):
            yield (
                st["content"]
                if not split_role
                else role_map.get(st["role"], "") + st["content"]
            )
        else:
            str_tmp = StringIO()
            for s in st["content"]:
                if s["type"] == "text" and s.get("text") is not None:
                    stc: str = (
                        s["text"]
                        if not split_role
                        else role_map.get(st["role"], "") + s["text"]
                    )
                    if full_message:
                        str_tmp.write(stc)
                    else:
                        yield stc
            if full_message:
                yield str_tmp.getvalue()
    return ""


def get_tokens(
    memory: CONTENT_LIST_TYPE,
    response: UniResponse[str, None],
    config: AmritaConfig | None = None,
) -> UniResponseUsage[int] | None:
    """Calculate token counts for messages and response

    Args:
        memory: Message history list
        response: Model response
        config: Optional configuration to use (uses default if not provided)

    Returns:
        Object containing token usage information
    """
    if (
        response.usage is not None
        and response.usage.total_tokens is not None
        and response.usage.completion_tokens is not None
        and response.usage.prompt_tokens is not None
    ):
        return response.usage
    config = config or get_config()
    if config.function_config.no_tokenizer:
        return
    it = hybrid_token_count(
        "".join(text_generator(memory, full_message=True)),
        config.llm.tokens_count_mode,
        tokenizer_type=config.function_config.tokenizer_used,
    )

    ot = hybrid_token_count(
        response.content,
        config.llm.tokens_count_mode,
        tokenizer_type=config.function_config.tokenizer_used,
    )
    return UniResponseUsage(
        prompt_tokens=it, total_tokens=it + ot, completion_tokens=ot
    )


def _validate_msg_list(
    messages: Sequence[typing.Any],
    thinking_config: ThinkingConfig | None = None,
) -> CONTENT_LIST_TYPE:
    """Validate a list of message dictionaries and convert them to Message objects.

    Args:
        messages (Sequence[Any]): List of message dictionaries or Message objects
        thinking_config (ThinkingConfig | None): Thinking config to filter reasoning_content

    Returns:
        CONTENT_LIST_TYPE: List of validated Message objects

    Raises:
        ValueError: If a message dictionary is invalid
    """
    validated_messages: CONTENT_LIST_TYPE = []
    for msg in messages:
        if isinstance(msg, dict):
            # Ensure message has role field
            if "role" not in msg:
                raise ValueError("Message dictionary is missing 'role' field")
            try:
                validated_msg = (
                    Message.model_validate(msg)
                    if msg["role"] != "tool"
                    else ToolResult.model_validate(msg)
                )
            except ValidationError as e:
                raise ValueError(f"Invalid message format: {e}")
            validated_messages.append(validated_msg)
        elif isinstance(msg, CONTENT_LIST_TYPE_ITEM):
            validated_messages.append(msg)
        else:
            raise TypeError(
                f"Invalid message type: {type(msg)}, this is not assignable to CONTENT_LIST_TYPE_ITEM"
            )

    # Filter reasoning_content according to thinking_config
    if thinking_config is not None and thinking_config.thinking_type == "enabled":
        for m in validated_messages:
            if not isinstance(m, Message):
                continue
            match thinking_config.content_mode:
                case "never":
                    m.reasoning_content = None
                case "by-tool":
                    if m.role == "assistant":
                        if m.tool_calls:
                            if m.reasoning_content is None:
                                raise ValueError(
                                    "by-tool mode: assistant with tool_calls must have reasoning_content"
                                )
                        else:
                            m.reasoning_content = None
                # "optional" -> no-op

    return validated_messages


async def _call_with_reflection(
    preset: ModelPreset,
    call_func: typing.Callable[[ModelAdapter], typing.Awaitable[T]],
    config: AmritaConfig,
) -> T:
    """Internal helper to call an adapter function with reflection and logging.

    Args:
        preset: Model preset to use for the call
        call_func: Async function to call on the adapter
        config: Configuration to pass to the adapter

    Returns:
        Result of the call function
    """
    adapter_class = AdapterManager().safe_get_adapter(preset.protocol)

    if adapter_class:
        if "text-gen" not in (ada_tp := adapter_class.get_type()):
            raise RuntimeError(
                f"Invalid adapter type for text-gen when using adapter: {adapter_class.__name__}, this adapter only supports {ada_tp}."
            )
        debug_log(
            f"Using adapter {adapter_class.__name__} to handle protocol {preset.protocol}"
        )

    else:
        raise ValueError(f"Undefined protocol adapter: {preset.protocol}")

    debug_log(f"Getting chat for {preset.model}")
    debug_log(f"Preset: {preset.name}")
    debug_log(f"Key: {preset.api_key[:7]}...")
    debug_log(f"Protocol: {preset.protocol}")
    debug_log(f"API URL: {preset.base_url}")
    debug_log(f"Model: {preset.model}")
    adapter = adapter_class(preset, config)
    return await call_func(adapter)


async def tools_caller(
    messages: CONTENT_LIST_TYPE,
    tools: list,
    preset: ModelPreset | None = None,
    tool_choice: ToolChoice | None = None,
    config: AmritaConfig | None = None,
) -> UniResponse[None, list[ToolCall] | None]:
    """Call tools using the specified model preset.

    Args:
        messages: List of messages to send to the model
        tools: List of available tools
        preset: Model preset to use (uses default if not provided)
        tool_choice: How to select tools (uses default if not provided)
        config: Configuration to use (uses default if not provided)

    Returns:
        Response containing tool calls or None
    """
    config = config or get_config()

    async def _call_tools(
        adapter: ModelAdapter,
    ):
        return await adapter.call_tools(messages, tools, tool_choice)

    preset = preset or PresetManager().get_default_preset()
    return await _call_with_reflection(
        preset,
        _call_tools,
        config,
    )


async def call_completion(
    messages: CONTENT_LIST_TYPE,
    preset: ModelPreset | None = None,
    config: AmritaConfig | None = None,
    **kwargs,
) -> AsyncGenerator[COMPLETION_RETURNING, None]:
    """Get chat response from the model.

    Args:
        messages: List of messages to send to the model
        preset: Model preset to use (uses default if not provided)
        config: Configuration to use (uses default if not provided)

    Yields:
        Individual response parts as strings or UniResponse objects
    """
    preset = preset or PresetManager().get_default_preset()
    config = config or get_config()
    messages = _validate_msg_list(messages, thinking_config=preset.thinking_config)

    async def _call_api(
        adapter: ModelAdapter,
    ) -> Callable[
        [], AsyncGenerator[MessageContent | str | UniResponse[str, None], typing.Any]
    ]:
        return lambda: adapter.call_api([(i.model_dump()) for i in messages], **kwargs)

    # Call adapter to get chat response
    response = await _call_with_reflection(preset, _call_api, config)
    is_thinking = False
    async for resp in response():
        if preset.config.cot_model:
            if isinstance(resp, str):
                if "<think>" in resp:
                    is_thinking = True
                    continue
                elif "</think>" in resp:
                    is_thinking = False
                    continue
        if not is_thinking:
            yield resp


async def get_last_response(
    generator: AsyncGenerator[RESPONSE_TYPE | UniResponse[str, None], None],
    yield_to: SuspendObjectStream[RESPONSE_TYPE] | None = None,
    yield_to_wrapper: Callable[[RESPONSE_TYPE], RESPONSE_TYPE] | None = None,
) -> UniResponse[str, None]:
    """Extract the last UniResponse from a response generator.

    Args:
        generator: Async generator yielding response parts

    Returns:
        The last UniResponse object from the generator

    Raises:
        RuntimeError: If no response is found in the generator
    """
    resp: UniResponse[str, None] | None = None
    async for chunk in generator:
        if isinstance(chunk, UniResponse):
            resp = chunk
        elif yield_to is not None:
            await yield_to.yield_response(
                chunk if not yield_to_wrapper else yield_to_wrapper(chunk)
            )

    if resp is None:
        raise RuntimeError("No response found in generator.")
    return resp


async def call_embedding(
    text: Sequence[str],
    preset: ModelPreset,
    config: AmritaConfig | None = None,
    **kwargs,
) -> Sequence[EmbeddingChunk]:
    config = config or get_config()
    if isinstance(text, str):
        raise TypeError("Text must be a sequence of strings, not a single string.")

    async def _call_embed(
        adapter: ModelAdapter,
    ) -> Sequence[EmbeddingChunk]:
        return await adapter.call_embed(text, **kwargs)

    return await _call_with_reflection(
        preset,
        _call_embed,
        config,
    )
