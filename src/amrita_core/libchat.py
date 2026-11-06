from __future__ import annotations

import typing
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator, Sequence
from io import StringIO

from amrita_sense.hook.matcher import MatcherFactory
from amrita_sense.logging import debug_log, logger
from amrita_sense.streaming import SuspendObjectStream
from pydantic import ValidationError

from amrita_core.base.adapter import (
    AGENTIC_RETURNING,
    COMPLETION_RETURNING,
    AdapterManager,
    FeatureFlag,
    MessageContent,
    ModelAdapter,
)
from amrita_core.exceptions import (
    ContextOverflowError,
    UnsupportedContentError,
    is_context_overflow_error,
)
from amrita_core.hook.event import (
    CompletionFallbackContext,
    EmbeddingFallbackContext,
    FallbackContext,
    ToolsFallbackContext,
)
from amrita_core.hook.exception import FallbackFailed
from amrita_core.preset import PresetManager
from amrita_core.usage import SessionUsageProxy
from amrita_core.utils import _did_you_mean_hint

from .config import AmritaConfig, get_config
from .tools.models import ToolChoice, ToolFunctionSchema
from .types import (
    CONTENT_LIST_TYPE,
    Content,
    EmbeddingChunk,
    Message,
    ModelPreset,
    TextContent,
    ThinkingConfig,
    ToolCall,
    ToolResult,
    UniResponse,
)
from .types.tool import DEGRADED_BLOCK_NOTE, block_label

T = typing.TypeVar("T")

RESPONSE_TYPE: typing.TypeAlias = str | MessageContent

#  Degrade reasons already warned about, so one reason does not flood every request.
_DEGRADE_WARNED: set[tuple[str, str]] = set()

#: Placeholder left where an untransportable block was removed; one fixed string for all kinds.
MULTIMODAL_UNSUPPORTED_PLACEHOLDER = "[Image Unsupported]"


def _warn_degrade_once(protocol: str, kind: str) -> None:
    """按 (协议, 载荷种类) 去重地提示一次降级。"""
    key = (protocol, kind)
    if key in _DEGRADE_WARNED:
        return
    _DEGRADE_WARNED.add(key)
    logger.warning(
        f"Adapter `{protocol}` declares no {kind} support; non-text blocks in this"
        " turn are replaced with a text placeholder in the outgoing payload."
        " The stored history is left untouched."
    )


def _degrade_blocks(content: list[Content]) -> list[Content]:
    """把非文本块换成文本说明；文本块原样保留。

    标签走 :func:`block_label`，与 :func:`content_text` 保持同一套叫法——模型在这
    一轮读到 ``<image omitted…>``、下一轮读到 ``<image_url omitted…>``，会把同一张
    图当成两种东西。
    """
    degraded: list[Content] = []
    for block in content:
        if isinstance(block, TextContent):
            degraded.append(block)
        else:
            degraded.append(
                TextContent(text=DEGRADED_BLOCK_NOTE.format(kind=block_label(block)))
            )
    return degraded


def filter_multimodal(
    context: CONTENT_LIST_TYPE, adapter: type[ModelAdapter]
) -> CONTENT_LIST_TYPE:
    """Replace every non-text block the adapter cannot carry with a placeholder.

    Public counterpart of the gateway's own negotiation, for callers that build
    a payload themselves (custom strategies, replay tools, tests) and need the
    same answer as :func:`call_completion` would give: a ``tool`` result is
    judged by ``tool_result_multimodal``, every other message by
    ``input_multimodal``, and the original objects are never mutated — the
    stored history keeps its blocks.

    Args:
        context: The message list to filter.
        adapter: Adapter class whose ``features`` decide what survives.

    Returns:
        The original list when the adapter carries everything, otherwise a new
        list where each untransportable block became
        ``TextContent(text=MULTIMODAL_UNSUPPORTED_PLACEHOLDER)``.
    """
    features = adapter.features
    if features.input_multimodal and features.tool_result_multimodal:
        return context

    filtered: CONTENT_LIST_TYPE = []
    for item in context:
        supported = (
            features.tool_result_multimodal
            if isinstance(item, ToolResult)
            else features.input_multimodal
        )
        if supported or not isinstance(item.content, list):
            filtered.append(item)
            continue
        if all(isinstance(block, TextContent) for block in item.content):
            filtered.append(item)
            continue
        filtered.append(
            item.model_copy(
                update={
                    "content": [
                        block
                        if isinstance(block, TextContent)
                        else TextContent(text=MULTIMODAL_UNSUPPORTED_PLACEHOLDER)
                        for block in item.content
                    ]
                }
            )
        )
    return filtered


def _unsupported_tool_result(
    messages: CONTENT_LIST_TYPE, preset: ModelPreset
) -> UnsupportedContentError | None:
    """Collect the tool-result blocks this turn cannot send.

    Collection only: the caller needs the full list at once, since raising per
    block would turn one request into several retries over the same payload.
    """
    kinds: set[str] = set()
    tool_call_ids: list[str] = []
    for item in messages:
        if not isinstance(item, ToolResult) or not isinstance(item.content, list):
            continue
        unsupported = [
            block for block in item.content if not isinstance(block, TextContent)
        ]
        if not unsupported:
            continue
        kinds.update(block_label(block) for block in unsupported)
        tool_call_ids.append(item.tool_call_id)
    if not tool_call_ids:
        return None
    return UnsupportedContentError(
        protocol=preset.protocol,
        scope="tool_result",
        kinds=tuple(sorted(kinds)),
        tool_call_ids=tuple(tool_call_ids),
    )


def _prepare_payload(
    messages: CONTENT_LIST_TYPE, preset: ModelPreset
) -> CONTENT_LIST_TYPE:
    """Prepare this turn's payload against the target adapter's declarations.

    The gateway is the adapter's direct consumer, so capability negotiation lives
    only here; strategies and storage always handle the standard models.

    Unsupported content takes two different paths:

    - **non-text blocks in a tool result** raise :class:`UnsupportedContentError`.
      Replacing them with a placeholder would let the model answer about an image
      it never received; the agent loop turns the error into a text tool result
      so the model can choose another return shape or another tool.
    - **non-text blocks in an ordinary message** are still degraded on a copy.
      The input already happened, so keeping the turn beats aborting it; the
      history in ``MemoryModel`` keeps its blocks for a stronger adapter later.
    """
    adapter_cls = AdapterManager().safe_get_adapter(preset.protocol)
    features = adapter_cls.features if adapter_cls else FeatureFlag()
    if features.input_multimodal and features.tool_result_multimodal:
        return messages

    if not features.tool_result_multimodal:
        unsupported = _unsupported_tool_result(messages, preset)
        if unsupported is not None:
            raise unsupported

    if features.input_multimodal:
        return messages

    prepared: CONTENT_LIST_TYPE = []
    for item in messages:
        if isinstance(item, ToolResult) or not isinstance(item.content, list):
            prepared.append(item)
            continue
        needs_degrade = any(
            not isinstance(block, TextContent) for block in item.content
        )
        if not needs_degrade:
            prepared.append(item)
            continue
        _warn_degrade_once(preset.protocol, "input_multimodal")
        prepared.append(
            item.model_copy(update={"content": _degrade_blocks(item.content)})
        )
    return prepared


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


def _normalize_message_content(msg: Message) -> None:
    """Strip empty content items from a message whose content is a list."""
    if isinstance(msg.content, list):
        msg.content = [c for c in msg.content if c]


def _register_assistant_tool_calls(msg: Message, tool_pairs: dict[str, str]) -> None:
    """Register tool_call_id -> function_name pairs from an assistant message.

    Pairs are registered whenever ``tool_calls`` is present, even alongside
    content: providers may return both in one message, and dropping the pairs
    in that case makes the following tool messages look unmatched.

    Raises ValueError if the message is assistant with no content and no tool_calls.
    """
    if msg.role != "assistant":
        return
    if msg.tool_calls:
        tool_pairs.update({tc.id: tc.function.name for tc in msg.tool_calls})
        return
    if msg.content is None:
        raise ValueError("Assistant message must have content or tool_calls")


_MAX_PAYLOAD_CHARS = 500


def _format_payload(it: int, messages: Sequence[typing.Any]) -> str:
    """Format a payload location string, truncating large bodies."""
    if it == -1:
        return "Unknown"
    raw = str(messages[it])
    if len(raw) > _MAX_PAYLOAD_CHARS:
        raw = raw[:_MAX_PAYLOAD_CHARS] + "...<truncated>"
    return f"{it}: {raw}"


def _validate_msg_list(
    messages: Sequence[typing.Any],
    thinking_config: ThinkingConfig | None = None,
) -> CONTENT_LIST_TYPE:
    """Validate a list of message dictionaries and convert them to Message objects.

    Args:
        messages: List of message dictionaries or Message objects.
        thinking_config: Thinking config to filter reasoning_content.

    Returns:
        List of validated Message/ToolResult objects.

    Raises:
        ValueError: If a message dictionary is invalid or tool-call pairing fails.
        TypeError: If a message has an unrecognised type.
    """
    validated_messages: CONTENT_LIST_TYPE = []
    it = -1
    try:
        tool_pairs: dict[str, str] = {}
        for it, msg in enumerate(messages):
            if isinstance(msg, dict):
                if "role" not in msg:
                    raise ValueError("Message dictionary is missing 'role' field")
                validated_msg = (
                    Message.model_validate(msg)
                    if msg["role"] != "tool"
                    else ToolResult.model_validate(msg)
                )
                validated_messages.append(validated_msg)

                if isinstance(validated_msg, Message):
                    _normalize_message_content(validated_msg)
                    _register_assistant_tool_calls(validated_msg, tool_pairs)
                if validated_msg.role == "tool":
                    pl = tool_pairs.pop(validated_msg.tool_call_id, None)
                    if pl is None:
                        raise ValueError(
                            f"Tool message {validated_msg.tool_call_id}@{it} must"
                            " have a matching tool_call_id in a previous"
                            " assistant message"
                        )

            elif isinstance(msg, (Message, ToolResult)):
                validated_messages.append(msg)
                if isinstance(msg, Message):
                    _normalize_message_content(msg)
                    _register_assistant_tool_calls(msg, tool_pairs)
                if msg.role == "tool":
                    pl = tool_pairs.pop(msg.tool_call_id, None)
                    if pl is None:
                        raise ValueError(
                            f"Tool message {msg.tool_call_id}@{it} must have a"
                            " matching tool_call_id in a previous assistant message"
                        )

            else:
                raise TypeError(
                    f"Invalid message type: {type(msg)}, this is not assignable"
                    " to CONTENT_LIST_TYPE_ITEM"
                )

        if tool_pairs:
            raise ValueError(
                "Tool call ids@tool:"
                f" {[f'{k}@{v}' for k, v in tool_pairs.items()]} do not have"
                " matching tool messages"
            )
    except ValidationError as e:
        details = _format_validation_errors(e)
        raise ValueError(
            f"Payload at {_format_payload(it, messages)}: {details}"
        ) from e

    _apply_thinking_filter(validated_messages, thinking_config)
    return validated_messages


def _format_validation_errors(e: ValidationError) -> str:
    """Extract human-readable details from a pydantic ValidationError."""
    parts: list[str] = []
    for err in e.errors():
        loc = ".".join(str(seg) for seg in err["loc"])
        msg = err.get("msg", "Unknown error")
        parts.append(f"{loc}: {msg}")
    return "; ".join(parts) if parts else str(e)


def _apply_thinking_filter(
    validated_messages: CONTENT_LIST_TYPE,
    thinking_config: ThinkingConfig | None,
) -> None:
    """Filter reasoning_content according to thinking_config.

    IMPORTANT: the filter must never mutate the original ``Message`` objects
    in place.  The message list is shared with the strategy context (e.g.
    ``ctx.message.unwrap()``), and providers like DeepSeek require the
    assistant ``reasoning_content`` to be passed back verbatim on subsequent
    requests — stripping it from the live objects would cause HTTP 400
    ("The `reasoning_content` in the thinking mode must be passed back").
    Modified messages are therefore shallow-copied into the validated list.
    """
    if thinking_config is None or thinking_config.thinking_type != "enabled":
        return
    for idx, m in enumerate(validated_messages):
        if not isinstance(m, Message):
            continue
        new_value: str | None = m.reasoning_content
        match thinking_config.content_mode:
            case "never":
                new_value = None
            case "by-tool":
                if m.role == "assistant":
                    if m.tool_calls:
                        if m.reasoning_content is None:
                            raise ValueError(
                                "by-tool mode: assistant with tool_calls must"
                                " have reasoning_content"
                            )
                    else:
                        new_value = None
            # "optional" -> no-op (keep original value)
        if new_value is not m.reasoning_content:
            # Shallow copy so the original object keeps its reasoning_content.
            copy = m.model_copy(deep=False)
            copy.reasoning_content = new_value
            validated_messages[idx] = copy


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

    if not adapter_class:
        raise ValueError(
            f"Undefined protocol adapter: {preset.protocol}. {_did_you_mean_hint(preset.protocol, list(AdapterManager().get_adapters().keys()))}"
        )
    debug_log(
        f"Using adapter {adapter_class.__name__} to handle protocol {preset.protocol}"
    )

    debug_log(f"Getting chat for {preset.model}")
    debug_log(f"Preset: {preset.name}")
    debug_log(f"Key: {preset.api_key[: min(int(len(preset.api_key) / 5), 4)]}...")
    debug_log(f"Protocol: {preset.protocol}")
    debug_log(f"API URL: {preset.base_url}")
    debug_log(f"Model: {preset.model}")
    adapter = adapter_class(preset, config)
    return await call_func(adapter)


async def _fire_fallback(
    preset: ModelPreset,
    exc: BaseException,
    config: AmritaConfig,
    term: int,
    ctx_factory: Callable[[ModelPreset, BaseException, int], FallbackContext],
) -> ModelPreset:
    """Fire a ``PRESET_FALLBACK`` event and resolve the replacement preset.

    Matchers registered via ``@on_preset_fallback()`` may swap ``ctx.preset``
    to retry with an alternative preset.  When no matcher replaces it (or no
    matcher is registered at all), ``FallbackFailed`` is raised.

    Args:
        preset: The preset that just failed.
        exc: The exception that caused the failure.
        config: Config providing ``llm.max_fallbacks`` / ``llm.max_retries``.
        term: Current attempt number (starting from 1).
        ctx_factory: Builds the concrete ``FallbackContext`` subclass for the
            failing gateway call (completion / tools / embedding).

    Returns:
        The replacement preset chosen by the matcher.
    """
    ctx = ctx_factory(preset, exc, term)
    await MatcherFactory.trigger_event(
        ctx, ctx.config, exception_ignored=(FallbackFailed,)
    )
    if ctx.preset is preset:
        ctx.fail("No preset fallback available, exiting!")
    return ctx.preset


async def _with_preset_fallback(
    preset: ModelPreset,
    config: AmritaConfig,
    ctx_factory: Callable[[ModelPreset, BaseException, int], FallbackContext],
    attempt: Callable[[ModelPreset], Awaitable[T]],
) -> T:
    """Run an adapter call wrapped in the gateway preset-fallback loop.

    Args:
        preset: Initial preset to try.
        config: Config providing ``llm.max_fallbacks``.
        ctx_factory: Builds the concrete ``FallbackContext`` subclass.
        attempt: Coroutine performing one call with the given preset.

    Returns:
        The result of the first successful attempt.

    Raises:
        FallbackFailed: When no preset fallback is available or every attempt
            fails.
    """
    for i in range(1, config.llm.max_fallbacks + 1):
        try:
            return await attempt(preset)
        except Exception as e:  # noqa: PERF203 -- fallback loop must retry on failure
            if isinstance(e, UnsupportedContentError):
                # A capability gap is not a transport failure, so do not spend the fallback budget.
                raise
            logger.warning(
                f"Because of `{e!s}`, LLM request failed, retrying ({i}/{config.llm.max_fallbacks})..."
            )
            preset = await _fire_fallback(preset, e, config, i, ctx_factory)
    raise FallbackFailed("Max preset fallbacks retries exceeded.")


async def tools_caller(
    messages: CONTENT_LIST_TYPE,
    tools: list[ToolFunctionSchema],
    preset: ModelPreset | None = None,
    tool_choice: ToolChoice | None = None,
    config: AmritaConfig | None = None,
    usage: SessionUsageProxy | None = None,
) -> UniResponse[str | None, list[ToolCall] | None]:
    """Call tools using the specified model preset.

    Args:
        messages: List of messages to send to the model
        tools: List of available tools
        preset: Model preset to use (uses default if not provided)
        tool_choice: How to select tools (uses default if not provided)
        config: Configuration to use (uses default if not provided)
        usage: Optional run-scoped usage proxy; when given, the response's
            provider usage is recorded before returning.

    Returns:
        Response containing tool calls or None
    """
    config = config or get_config()
    preset = preset or PresetManager().get_default_preset()

    async def _attempt(
        current_preset: ModelPreset,
    ) -> UniResponse[str | None, list[ToolCall] | None]:
        validated = _validate_msg_list(
            messages, thinking_config=current_preset.thinking_config
        )
        # Re-negotiate per attempt: fallback may switch to a preset with another protocol.
        payload = _prepare_payload(validated, current_preset)

        async def _call_tools(
            adapter: ModelAdapter,
        ):
            return await adapter.call_tools(payload, tools, tool_choice)

        resp = await _call_with_reflection(current_preset, _call_tools, config)
        if usage is not None and resp.usage is not None:
            usage.record(
                resp.usage,
                model=resp.metadata.model,
                preset_name=current_preset.name,
                rate=current_preset.rate,
                request_id=resp.metadata.original_request_id,
            )
        return resp

    return await _with_preset_fallback(
        preset,
        config,
        lambda p, e, i: ToolsFallbackContext(p, e, config, messages, i, tools=tools),
        _attempt,
    )


async def call_completion(
    messages: CONTENT_LIST_TYPE,
    preset: ModelPreset | None = None,
    config: AmritaConfig | None = None,
    usage: SessionUsageProxy | None = None,
    **kwargs,
) -> AsyncGenerator[COMPLETION_RETURNING, None]:
    """Get chat response from the model.

    Args:
        messages: List of messages to send to the model
        preset: Model preset to use (uses default if not provided)
        config: Configuration to use (uses default if not provided)
        usage: Optional run-scoped usage proxy; the trailing ``UniResponse``
            (by convention the last yielded value) is recorded when given.

    Yields:
        Individual response parts as strings or UniResponse objects
    """
    preset = preset or PresetManager().get_default_preset()
    config = config or get_config()

    async def _attempt(
        current_preset: ModelPreset,
    ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
        validated = _validate_msg_list(
            messages, thinking_config=current_preset.thinking_config
        )
        payload = _prepare_payload(validated, current_preset)

        async def _call_api(
            adapter: ModelAdapter,
        ) -> Callable[
            [],
            AsyncGenerator[COMPLETION_RETURNING, typing.Any],
        ]:
            if (
                "text-gen" != adapter.get_type()
                and "text-gen" not in adapter.get_type()
            ):
                raise ValueError(
                    f"Model adapter {adapter.get_type()} does not support text-gen"
                )
            return lambda: adapter.call_api(
                [(i.model_dump()) for i in payload], **kwargs
            )

        # Call adapter to get chat response
        response = await _call_with_reflection(current_preset, _call_api, config)
        is_thinking = False
        async for resp in response():
            if current_preset.config.cot_model:
                if isinstance(resp, str):
                    if "<think>" in resp:
                        is_thinking = True
                        continue
                    elif "</think>" in resp:
                        is_thinking = False
                        continue
            if not is_thinking:
                if isinstance(resp, UniResponse) and usage is not None:
                    if resp.usage is not None:
                        usage.record(
                            resp.usage,
                            model=resp.metadata.model,
                            preset_name=current_preset.name,
                            rate=current_preset.rate,
                            request_id=resp.metadata.original_request_id,
                        )
                yield resp

    emitted = False
    for i in range(1, config.llm.max_fallbacks + 1):
        try:
            async for chunk in _attempt(preset):
                if not isinstance(chunk, UniResponse):
                    emitted = True
                yield chunk
            return
        except Exception as e:  # noqa: PERF203 -- fallback loop must retry the stream on failure
            if emitted:
                # Chunks already reached the caller; a retry would stack a second answer.
                raise
            if is_context_overflow_error(e):
                # Another preset cannot shrink the request, so surface it instead of burning the whole fallback budget on it.
                raise ContextOverflowError(str(e)) from e
            logger.warning(
                f"Because of `{e!s}`, LLM request failed, retrying ({i}/{config.llm.max_fallbacks})..."
            )
            preset = await _fire_fallback(
                preset,
                e,
                config,
                i,
                lambda p, exc, term: CompletionFallbackContext(
                    p, exc, config, messages, term
                ),
            )
    raise FallbackFailed("Max preset fallbacks retries exceeded.")


async def agentic_call_completion(
    messages: CONTENT_LIST_TYPE,
    tools: list[ToolFunctionSchema] | None = None,
    tool_choice: ToolChoice | None = None,
    preset: ModelPreset | None = None,
    config: AmritaConfig | None = None,
    usage: SessionUsageProxy | None = None,
    **kwargs,
) -> AsyncGenerator[AGENTIC_RETURNING, None]:
    """Stream text and tool calls from one request.

    Same contract as :func:`call_completion` (preset fallback, usage
    accounting, thinking-content filtering), except the trailing
    ``UniResponse`` may also carry ``tool_calls`` and text keeps streaming while
    they are assembled. Adapters whose ``features.agentic_call`` is unset fail fast
    with ``NotImplementedError`` before any request is sent, so callers can fall
    back to the legacy tool-calling path.

    Args:
        messages: List of messages to send to the model
        tools: Tool definitions to expose; ``None``/empty means a plain text turn
        tool_choice: How to select tools
        preset: Model preset to use (uses default if not provided)
        config: Configuration to use (uses default if not provided)
        usage: Optional run-scoped usage proxy; the trailing ``UniResponse``
            (by convention the last yielded value) is recorded when given.

    Yields:
        Individual response parts as strings or UniResponse objects
    """
    preset = preset or PresetManager().get_default_preset()
    config = config or get_config()

    async def _attempt(
        current_preset: ModelPreset,
    ) -> AsyncGenerator[AGENTIC_RETURNING, None]:
        validated = _validate_msg_list(
            messages, thinking_config=current_preset.thinking_config
        )
        payload = _prepare_payload(validated, current_preset)

        async def _call_api(
            adapter: ModelAdapter,
        ) -> Callable[
            [],
            AsyncGenerator[AGENTIC_RETURNING, typing.Any],
        ]:
            if not adapter.features.agentic_call:
                raise NotImplementedError(
                    f"Model adapter {adapter.get_type()} does not support"
                    " agentic_call_api"
                )
            if (
                "text-gen" != adapter.get_type()
                and "text-gen" not in adapter.get_type()
            ):
                raise ValueError(
                    f"Model adapter {adapter.get_type()} does not support text-gen"
                )
            return lambda: adapter.agentic_call_api(
                [(i.model_dump()) for i in payload],
                tools=tools,
                tool_choice=tool_choice,
                **kwargs,
            )

        response = await _call_with_reflection(current_preset, _call_api, config)
        is_thinking = False
        async for resp in response():
            if current_preset.config.cot_model:
                if isinstance(resp, str):
                    if "<think>" in resp:
                        is_thinking = True
                        continue
                    elif "</think>" in resp:
                        is_thinking = False
                        continue
            if not is_thinking:
                if isinstance(resp, UniResponse) and usage is not None:
                    if resp.usage is not None:
                        usage.record(
                            resp.usage,
                            model=resp.metadata.model,
                            preset_name=current_preset.name,
                            rate=current_preset.rate,
                            request_id=resp.metadata.original_request_id,
                        )
                yield resp

    emitted = False
    for i in range(1, config.llm.max_fallbacks + 1):
        try:
            async for chunk in _attempt(preset):
                if not isinstance(chunk, UniResponse):
                    emitted = True
                yield chunk
            return
        except Exception as e:  # noqa: PERF203 -- fallback loop must retry the stream on failure
            if emitted:
                # Chunks already reached the caller; a retry would stack a second answer.
                raise
            if isinstance(e, (NotImplementedError, UnsupportedContentError)):
                # Not a provider failure: swapping presets cannot add support.
                raise
            if is_context_overflow_error(e):
                raise ContextOverflowError(str(e)) from e
            logger.warning(
                f"Because of `{e!s}`, LLM request failed, retrying ({i}/{config.llm.max_fallbacks})..."
            )
            preset = await _fire_fallback(
                preset,
                e,
                config,
                i,
                lambda p, exc, term: CompletionFallbackContext(
                    p, exc, config, messages, term
                ),
            )
    raise FallbackFailed("Max preset fallbacks retries exceeded.")


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

    async def _attempt(
        current_preset: ModelPreset,
    ) -> Sequence[EmbeddingChunk]:
        async def _call_embed(
            adapter: ModelAdapter,
        ) -> Sequence[EmbeddingChunk]:
            if "embed" != adapter.get_type() and "embed" not in adapter.get_type():
                raise ValueError(
                    f"Model adapter {adapter.get_type()} does not support embedding"
                )
            return await adapter.call_embed(text, **kwargs)

        return await _call_with_reflection(
            current_preset,
            _call_embed,
            config,
        )

    return await _with_preset_fallback(
        preset,
        config,
        lambda p, e, i: EmbeddingFallbackContext(p, e, config, text, i),
        _attempt,
    )
