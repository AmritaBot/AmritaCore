from collections.abc import AsyncGenerator, Iterable

import openai
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

from amrita_core.config import get_config
from amrita_core.logging import debug_log
from amrita_core.protocol import ModelAdapter
from amrita_core.tools.models import ToolChoice, ToolFunctionSchema
from amrita_core.types import ToolCall, UniResponse, UniResponseUsage


class OpenAIAdapter(ModelAdapter):
    """OpenAI Protocol Adapter"""

    @override
    async def call_api(
        self, messages: Iterable[ChatCompletionMessageParam]
    ) -> AsyncGenerator[str | UniResponse[str, None], None]:
        """Call OpenAI API to get chat responses"""
        preset = self.preset
        client = openai.AsyncOpenAI(
            base_url=preset.base_url,
            api_key=preset.api_key,
            timeout=get_config().llm.llm_timeout,
            max_retries=get_config().llm.max_retries,
        )
        completion: ChatCompletion | openai.AsyncStream[ChatCompletionChunk] | None = (
            None
        )
        if stream := preset.config.stream:
            completion = await client.chat.completions.create(
                model=preset.model,
                messages=messages,
                max_tokens=get_config().llm.max_tokens,
                stream=stream,
                stream_options={"include_usage": True},
            )
        else:
            completion = await client.chat.completions.create(
                model=preset.model,
                messages=messages,
                max_tokens=get_config().llm.max_tokens,
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
                    if chunk.choices[0].delta.content is not None:
                        response += chunk.choices[0].delta.content
                        yield chunk.choices[0].delta.content
                        debug_log(chunk.choices[0].delta.content)
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
        uni_response = UniResponse(
            role="assistant",
            content=response,
            usage=uni_usage,
            tool_calls=None,
        )
        yield uni_response

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

        preset = self.preset
        base_url = preset.base_url
        key = preset.api_key
        model = preset.model
        client = openai.AsyncOpenAI(
            base_url=base_url,
            api_key=key,
            timeout=get_config().llm.llm_timeout,
        )
        completion: ChatCompletion = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False,
            tool_choice=choice,
            tools=tools,
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
    def get_adapter_protocol() -> tuple[str, ...]:
        return "openai", "__main__"
