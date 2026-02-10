from __future__ import annotations

import typing
from collections.abc import AsyncGenerator, Generator

from pydantic import ValidationError

from amrita_core.preset import PresetManager

from .config import AmritaConfig, get_config
from .logging import debug_log
from .protocol import (
    AdapterManager,
    ModelAdapter,
)
from .tokenizer import hybrid_token_count
from .tools.models import ToolChoice
from .types import (
    CONTENT_LIST_TYPE,
    Message,
    ModelPreset,
    ToolCall,
    ToolResult,
    UniResponse,
    UniResponseUsage,
)

T = typing.TypeVar("T")


def text_generator(
    memory: CONTENT_LIST_TYPE, split_role: bool = False
) -> Generator[str, None, str]:
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
            for s in st["content"]:
                if s["type"] == "text" and s.get("text") is not None:
                    yield (
                        s["text"]
                        if not split_role
                        else role_map.get(st["role"], "") + s["text"]
                    )
    return ""


async def get_tokens(
    memory: CONTENT_LIST_TYPE,
    response: UniResponse[str, None],
    config: AmritaConfig | None = None,
) -> UniResponseUsage[int]:
    """Calculate token counts for messages and response

    Args:
        memory: Message history list
        response: Model response

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
    it = hybrid_token_count(
        "".join(list(text_generator(memory))),
        config.llm.tokens_count_mode,
    )

    ot = hybrid_token_count(response.content)
    return UniResponseUsage(
        prompt_tokens=it, total_tokens=it + ot, completion_tokens=ot
    )


def _validate_msg_list(
    messages: CONTENT_LIST_TYPE,
) -> CONTENT_LIST_TYPE:
    validated_messages = []
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
        else:
            validated_messages.append(msg)
    return validated_messages


async def _call_with_reflection(
    preset: ModelPreset,
    call_func: typing.Callable[..., typing.Awaitable[T]],
    config: AmritaConfig,
    *args,
    **kwargs,
) -> T:
    """Call the specified function with the list of presets"""
    adapter_class = AdapterManager().safe_get_adapter(preset.protocol)
    if adapter_class:
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
    return await call_func(adapter, *args, **kwargs)


async def tools_caller(
    messages: CONTENT_LIST_TYPE,
    tools: list,
    preset: ModelPreset | None = None,
    tool_choice: ToolChoice | None = None,
    config: AmritaConfig | None = None,
) -> UniResponse[None, list[ToolCall] | None]:
    config = config or get_config()

    async def _call_tools(
        adapter: ModelAdapter,
        messages: CONTENT_LIST_TYPE,
        tools,
        tool_choice,
    ):
        return await adapter.call_tools(messages, tools, tool_choice)

    preset = preset or PresetManager().get_default_preset()
    return await _call_with_reflection(
        preset, _call_tools, config, messages, tools, tool_choice
    )


async def call_completion(
    messages: CONTENT_LIST_TYPE,
    preset: ModelPreset | None = None,
    config: AmritaConfig | None = None,
) -> AsyncGenerator[str | UniResponse[str, None], None]:
    """Get chat response"""
    messages = _validate_msg_list(messages)
    preset = preset or PresetManager().get_default_preset()
    config = config or get_config()

    async def _call_api(adapter: ModelAdapter, messages: CONTENT_LIST_TYPE):
        async def inner():
            async for i in adapter.call_api([(i.model_dump()) for i in messages]):
                yield i

        return inner

    # Call adapter to get chat response
    response = await _call_with_reflection(preset, _call_api, config, messages)

    async for i in response():
        yield i


async def get_last_response(
    generator: AsyncGenerator[str | UniResponse[str, None], None],
) -> UniResponse[str, None]:
    ls: list[UniResponse[str, None]] = [
        i async for i in generator if isinstance(i, UniResponse)
    ]
    if len(ls) == 0:
        raise RuntimeError("No response found in generator.")
    return ls[-1]
