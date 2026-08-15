from collections.abc import AsyncGenerator, Iterable, Sequence
from typing import Literal, cast

import openai
from amrita_sense.logging import debug_log
from openai._types import SequenceNotStr
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_named_tool_choice_param import (
    ChatCompletionNamedToolChoiceParam,
)
from openai.types.chat.chat_completion_named_tool_choice_param import (
    Function as OPENAI_Function,
)
from openai.types.chat.chat_completion_tool_choice_option_param import (
    ChatCompletionToolChoiceOptionParam,
)
from typing_extensions import override

from amrita_core.base.adapter import (
    COMPLETION_RETURNING,
    ModelAdapter,
)
from amrita_core.config import AmritaConfig
from amrita_core.contents import MessageMetadataPayload, MessageWithMetadata
from amrita_core.tools.models import (
    ToolChoice,
    ToolFunctionSchema,
)
from amrita_core.types import (
    EmbeddingChunk,
    ModelConfig,
    ModelPreset,
    ToolCall,
    UniResponse,
    UniResponseUsage,
)
from amrita_core.types.response import STOP_REASON, RequestMetadata
from amrita_core.utils import model_dump

R2R_MAP: dict[
    Literal["stop", "length", "tool_calls", "content_filter", "function_call"],
    STOP_REASON,
] = {
    "stop": "stop_sequence",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "content_filter": "refusal",
    "function_call": "tool_use",  # WARNING: Backwards compatibility for legacy OpenAI API versions (pre-2023) that return 'function_call' instead of 'tool_calls'
}


class OpenAIAdapter(ModelAdapter):
    """OpenAI Protocol Adapter

    NOTE: Through OpenAI SDK, we are actually hard to get cache info, each providers' cache informations are different.
        So we will not provide `cache info` from OpenAIAdapter. By the way, `stop sequence` is not provided by OpenAI SDK,
        so we will not provide this too.

    """

    __override__ = True

    @override
    async def call_api(
        self,
        messages: Iterable[ChatCompletionMessageParam],
        stop: str | list[str] | None = None,
        **kwargs,
    ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
        """Call OpenAI API to get chat responses"""
        preset: ModelPreset = self.preset
        preset_config: ModelConfig = preset.config
        config: AmritaConfig = self.config
        messages = model_dump(messages)
        client = openai.AsyncOpenAI(
            base_url=preset.base_url,
            api_key=preset.api_key,
            timeout=config.llm.llm_timeout,
            max_retries=config.llm.max_retries,
        )
        completion: ChatCompletion | openai.AsyncStream[ChatCompletionChunk] | None = (
            None
        )

        kwargs.setdefault("extra_body", {})
        if preset.thinking_config is not None:
            if preset.thinking_config.thinking_type is not None:
                kwargs["extra_body"].setdefault("thinking", {}).setdefault(
                    "type", preset.thinking_config.thinking_type
                )
            if preset.thinking_config.enable_thinking:
                kwargs["extra_body"].setdefault("enable_thinking", True)

            if preset.thinking_config.thinking_effort:
                kwargs.update(
                    {"reasoning_effort": preset.thinking_config.thinking_effort}
                )

        if stream := preset.config.stream:
            kwargs.update({"stream_options": {"include_usage": True}})
        completion = await client.chat.completions.create(
            model=preset.model,
            messages=messages,
            max_tokens=config.llm.max_tokens,
            top_p=preset_config.top_p,
            temperature=preset_config.temperature,
            stream=stream,
            stop=stop,
            **kwargs,
        )
        response: str = ""
        reasoning: str | None = None
        uni_usage = None
        model_name: str = preset.model
        meta: RequestMetadata | None = None

        # Process streaming response
        if self.preset.config.stream and isinstance(completion, openai.AsyncStream):
            async with completion as completion:
                # Provider-specific request/trace ids: OpenAI uses
                # ``x-request-id``; DeepSeek uses ``x-ds-trace-id``/``eo-log-uuid``.
                headers = completion.response.headers
                req_id: str | None = (
                    headers.get("x-request-id")
                    or headers.get("x-ds-trace-id")
                    or headers.get("eo-log-uuid")
                    or getattr(completion, "_request_id", None)
                )
                async for chunk in completion:
                    try:
                        if chunk.choices[0].finish_reason is not None:
                            model_name = chunk.model
                            meta = RequestMetadata(
                                model=model_name,
                                original_request_id=req_id,
                                stop_sequence=None,
                                stop_reason=(
                                    R2R_MAP.get(chunk.choices[0].finish_reason)
                                    if chunk.choices[0].finish_reason
                                    else None
                                ),
                            )
                        if chunk.usage:
                            uni_usage = UniResponseUsage.model_validate(
                                chunk.usage, from_attributes=True
                            )

                        if (
                            reas_chunk := getattr(
                                chunk.choices[0].delta, "reasoning_content", None
                            )
                        ) is not None:
                            reas_chunk = str(reas_chunk)
                            if reasoning is None:
                                reasoning = reas_chunk
                            else:
                                reasoning += reas_chunk
                            yield MessageWithMetadata(
                                content=reas_chunk,
                                metadata=MessageMetadataPayload(
                                    type="reasoning_chunk", extra_type="cot_chunk"
                                ),
                            )
                        if (chunk := chunk.choices[0].delta.content) is not None:
                            response += chunk
                            yield chunk
                            debug_log(chunk)
                    except IndexError:
                        break

        else:
            if isinstance(completion, ChatCompletion):
                if (
                    reas_chunk := getattr(
                        completion.choices[0].message, "reasoning_content", None
                    )
                ) is not None:
                    reasoning = str(reas_chunk)
                    yield MessageWithMetadata(
                        content=reasoning,
                        metadata=MessageMetadataPayload(
                            type="reasoning_chunk", extra_type="cot_chunk"
                        ),
                    )
                meta = RequestMetadata(
                    model=completion.model,
                    original_request_id=completion._request_id,
                    stop_sequence=None,
                    stop_reason=(
                        R2R_MAP.get(completion.choices[0].finish_reason)
                        if completion.choices[0].finish_reason
                        else None
                    ),
                )
                response = (
                    completion.choices[0].message.content
                    if completion.choices[0].message.content is not None
                    else ""
                )
                debug_log(response)
                yield response
                if completion.usage:
                    uni_usage = UniResponseUsage.model_validate(
                        completion.usage, from_attributes=True
                    )
            else:
                raise RuntimeError("Received unexpected response type")
        yield UniResponse(
            role="assistant",
            content=response,
            usage=uni_usage,
            tool_calls=None,
            reasoning_content=reasoning,
            metadata=meta or RequestMetadata(model=preset.model),
        )

    @override
    async def call_tools(
        self,
        messages: Iterable,
        tools: list,
        tool_choice: ToolChoice | None = None,
        **kwargs,
    ) -> UniResponse[None, list[ToolCall] | None]:
        if not tool_choice:
            choice: ChatCompletionToolChoiceOptionParam = "auto"
        elif isinstance(tool_choice, ToolFunctionSchema):
            choice = ChatCompletionNamedToolChoiceParam(
                function=OPENAI_Function(name=tool_choice.function.name),
                type=tool_choice.type,
            )
        else:
            choice = tool_choice
        messages = model_dump(messages)
        config: AmritaConfig = self.config
        preset: ModelPreset = self.preset
        preset_config: ModelConfig = preset.config
        base_url: str = preset.base_url
        key: str = preset.api_key
        model: str = preset.model
        client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key=key,
            timeout=config.llm.llm_timeout,
        )
        kwargs.setdefault("extra_body", {})
        if preset.thinking_config is not None:
            if preset.thinking_config.thinking_type is not None:
                kwargs["extra_body"].setdefault("thinking", {}).setdefault(
                    "type", preset.thinking_config.thinking_type
                )
            if preset.thinking_config.enable_thinking:
                kwargs["extra_body"].setdefault("enable_thinking", True)

            if preset.thinking_config.thinking_effort:
                kwargs.update(
                    {"reasoning_effort": preset.thinking_config.thinking_effort}
                )
        completion: ChatCompletion = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False,
            tool_choice=choice,
            tools=tools,
            top_p=preset_config.top_p,
            temperature=preset_config.temperature,
            **kwargs,
        )
        msg = completion.choices[0].message
        metadata = RequestMetadata(
            model=completion.model,
            original_request_id=completion._request_id,
            stop_sequence=None,
            stop_reason=(
                R2R_MAP.get(completion.choices[0].finish_reason)
                if completion.choices[0].finish_reason
                else None
            ),
        )
        return UniResponse(
            role="assistant",
            tool_calls=(
                [
                    ToolCall.model_validate(i, from_attributes=True)
                    for i in msg.tool_calls
                ]
                if msg.tool_calls
                else None
            ),
            content=None,
            reasoning_content=getattr(msg, "reasoning_content", None),
            usage=(
                UniResponseUsage.model_validate(completion.usage, from_attributes=True)
                if completion.usage
                else None
            ),
            metadata=metadata,
        )

    @override
    async def call_embed(
        self, texts: Sequence[str], **kwargs
    ) -> Sequence[EmbeddingChunk]:
        """Embedding interface"""
        if isinstance(texts, str):
            raise ValueError(
                "Texts cannot be string, please pass a sequence of strings"
            )
        config: AmritaConfig = self.config
        preset: ModelPreset = self.preset

        base_url: str = preset.base_url
        key: str = preset.api_key
        model: str = preset.model
        client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key=key,
            timeout=config.llm.llm_timeout,
        )
        text_seq = cast(SequenceNotStr, texts)
        response = await client.embeddings.create(input=text_seq, model=model, **kwargs)
        return [
            EmbeddingChunk.model_validate(i, from_attributes=True)
            for i in response.data
        ]

    @staticmethod
    def get_adapter_protocol() -> tuple[str, str]:
        return "openai", "__main__"
