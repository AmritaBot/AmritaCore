from collections.abc import AsyncGenerator, Iterable, Sequence
from io import StringIO
from typing import Any

import anthropic
import openai
from anthropic.types import TextBlock
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
from pydantic import BaseModel
from typing_extensions import override

from amrita_core.config import AmritaConfig
from amrita_core.logging import debug_log
from amrita_core.protocol import (
    COMPLETION_RETURNING,
    ModelAdapter,
)
from amrita_core.tools.models import ToolChoice, ToolFunctionSchema
from amrita_core.types import (
    ModelConfig,
    ModelPreset,
    ToolCall,
    UniResponse,
    UniResponseUsage,
)


def model_dump(obj: Iterable[BaseModel | dict]) -> Sequence[Any]:
    return [obj.model_dump() if isinstance(obj, BaseModel) else obj for obj in obj]


class AnthropicAdapter(ModelAdapter):
    """Anthropic Protocol Adapter"""

    @override
    async def call_api(
        self, messages: Iterable, *args, **kwargs
    ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
        """Call Anthropic API to get chat responses"""
        preset: ModelPreset = self.preset
        preset_config: ModelConfig = preset.config
        config: AmritaConfig = self.config
        client = anthropic.AsyncAnthropic(
            api_key=preset.api_key,
            base_url=preset.base_url,
            timeout=config.llm.llm_timeout,
            max_retries=config.llm.max_retries,
        )
        stream = preset_config.stream
        messages = model_dump(messages)
        text_resp = StringIO()
        if stream:
            async with client.messages.stream(
                model=preset.model,
                messages=messages,
                max_tokens=config.llm.max_tokens,
                top_p=preset_config.top_p,
                temperature=preset_config.temperature,
            ) as resp:
                async for chunk in resp.text_stream:
                    text_resp.write(chunk)
                    yield chunk
                last_rsp = await resp.get_final_message()
                last_rsp_usage = last_rsp.usage
            usage: UniResponseUsage[int] = UniResponseUsage(
                prompt_tokens=last_rsp_usage.input_tokens,
                completion_tokens=last_rsp_usage.output_tokens,
                total_tokens=last_rsp_usage.input_tokens + last_rsp_usage.output_tokens,
            )
        else:
            last_rsp = await client.messages.create(
                model=preset.model,
                messages=messages,
                max_tokens=config.llm.max_tokens,
                top_p=preset_config.top_p,
                temperature=preset_config.temperature,
            )
            for ct in last_rsp.content:
                if isinstance(ct, TextBlock):
                    text_resp.write(ct.text)
            usage: UniResponseUsage[int] = UniResponseUsage(
                prompt_tokens=last_rsp.usage.input_tokens,
                completion_tokens=last_rsp.usage.output_tokens,
                total_tokens=last_rsp.usage.input_tokens + last_rsp.usage.output_tokens,
            )
        yield UniResponse(content=text_resp.getvalue(), usage=usage, tool_calls=None)

    # TODO: call_tools method
    @staticmethod
    def get_adapter_protocol() -> str | tuple[str, ...]:
        return ("anthropic", "claude")


class OpenAIAdapter(ModelAdapter):
    """OpenAI Protocol Adapter"""

    __override__ = True

    @override
    async def call_api(
        self, messages: Iterable[ChatCompletionMessageParam], *args, **kwargs
    ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
        """Call OpenAI API to get chat responses"""
        preset: ModelPreset = self.preset
        preset_config: ModelConfig = preset.config
        config: AmritaConfig = self.config
        client = openai.AsyncOpenAI(
            base_url=preset.base_url,
            api_key=preset.api_key,
            timeout=config.llm.llm_timeout,
            max_retries=config.llm.max_retries,
        )
        completion: ChatCompletion | openai.AsyncStream[ChatCompletionChunk] | None = (
            None
        )
        if stream := preset.config.stream:
            completion = await client.chat.completions.create(
                model=preset.model,
                messages=messages,
                max_tokens=config.llm.max_tokens,
                top_p=preset_config.top_p,
                temperature=preset_config.temperature,
                stream=stream,
                stream_options={"include_usage": True},
            )
        else:
            completion = await client.chat.completions.create(
                model=preset.model,
                messages=messages,
                max_tokens=config.llm.max_tokens,
                top_p=preset_config.top_p,
                temperature=preset_config.temperature,
                stream=False,
            )
        response: str = ""
        uni_usage = None
        # Process streaming response
        if self.preset.config.stream and isinstance(completion, openai.AsyncStream):
            async for chunk in completion:
                try:
                    if chunk.usage:
                        uni_usage = UniResponseUsage.model_validate(
                            chunk.usage, from_attributes=True
                        )
                    if (chunk := chunk.choices[0].delta.content) is not None:
                        response += chunk
                        yield chunk
                        debug_log(chunk)
                except IndexError:
                    break
        else:
            debug_log(response)
            if isinstance(completion, ChatCompletion):
                response = (
                    completion.choices[0].message.content
                    if completion.choices[0].message.content is not None
                    else ""
                )
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
        )

    @override
    async def call_tools(
        self,
        messages: Iterable,
        tools: list,
        tool_choice: ToolChoice | None = None,
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
        completion: ChatCompletion = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False,
            tool_choice=choice,
            tools=tools,
            top_p=preset_config.top_p,
            temperature=preset_config.temperature,
        )
        msg = completion.choices[0].message
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
        )

    @staticmethod
    def get_adapter_protocol() -> tuple[str, str]:
        return "openai", "__main__"
