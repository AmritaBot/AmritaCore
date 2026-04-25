import json
from collections.abc import AsyncGenerator, Iterable, Sequence
from io import StringIO
from typing import Any

import anthropic
import openai
from anthropic.types import (
    MessageParam,
    TextBlock,
    ToolChoiceAnyParam,
    ToolChoiceAutoParam,
    ToolChoiceNoneParam,
    ToolChoiceParam,
    ToolChoiceToolParam,
    ToolUnionParam,
    ToolUseBlock,
)
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
from pydantic import BaseModel, Field
from typing_extensions import override

from amrita_core.config import AmritaConfig
from amrita_core.logging import debug_log
from amrita_core.protocol import (
    COMPLETION_RETURNING,
    ModelAdapter,
)
from amrita_core.tools.models import (
    FunctionParametersSchema,
    ToolChoice,
    ToolFunctionSchema,
)
from amrita_core.types import (
    Function,
    ModelConfig,
    ModelPreset,
    ToolCall,
    UniResponse,
    UniResponseUsage,
)


class AnthropicFunctionSchema(BaseModel):
    """Validate Anthropic function definition structure"""

    name: str = Field(..., description="Function name")
    description: str = Field(..., description="Function description")
    input_schema: FunctionParametersSchema = Field(
        ..., description="Function parameter definition"
    )
    strict: bool = Field(
        False, description="Whether this is a strict function (strict match)"
    )


def model_dump(obj: Iterable[BaseModel | dict]) -> Sequence[Any]:
    return [obj.model_dump() if isinstance(obj, BaseModel) else obj for obj in obj]


class AnthropicAdapter(ModelAdapter):
    """Anthropic Protocol Adapter"""

    @staticmethod
    def _convert_content_to_blocks(
        content: str | list[dict] | None,
    ) -> list[dict] | str:
        """Convert internal content to Anthropic content blocks (or plain string)"""
        if content is None:
            return []
        if isinstance(content, str):
            # Plain text -> single text block
            return [{"type": "text", "text": content}]
        # Content is a list (may contain TextContent, ImageContent, etc.)
        blocks = []
        for item in content:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "text":
                blocks.append({"type": "text", "text": item.get("text", "")})
            elif item_type == "image_url":
                # Support Anthropic image blocks if needed (example)
                image_url = item.get("image_url", {}).get("url", "")
                blocks.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": image_url,
                        },
                    }
                )
            # Other types are ignored for now
        return blocks or [{"type": "text", "text": ""}]

    @staticmethod
    def _convert_messages(internal_msgs: list[dict]) -> list[MessageParam]:
        """
        Convert internal (OpenAI-like) message format to Anthropic message list.

        Core rules:
        - system messages are kept directly (Anthropic supports role: "system")
        - user message content is converted to a content block array
        - assistant messages: if tool_calls are present, build tool_use blocks;
          otherwise convert to text blocks
        - tool messages: not emitted independently; merged with the preceding
          assistant message into a single user message containing tool_result blocks
        """
        converted = []
        temp_tool_results = []

        def flush_tool_results():
            """Pack collected tool results into a single user message"""
            nonlocal temp_tool_results
            if temp_tool_results:
                converted.append({"role": "user", "content": temp_tool_results})
                temp_tool_results = []

        for msg in internal_msgs:
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                flush_tool_results()
                # System content may be str or list; extract plain text
                if isinstance(content, list):
                    text = "".join(
                        item.get("text", "")
                        for item in content
                        if item.get("type") == "text"
                    )
                else:
                    text = content or ""
                converted.append({"role": "system", "content": text})

            elif role == "user":
                flush_tool_results()
                blocks = AnthropicAdapter._convert_content_to_blocks(content)
                converted.append({"role": "user", "content": blocks})

            elif role == "assistant":
                flush_tool_results()
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    blocks = []
                    for tc in tool_calls:
                        # tc may be a dict or ToolCall object
                        tc = tc if isinstance(tc, dict) else tc.model_dump()
                        func = tc.get("function", {})
                        blocks.append(
                            {
                                "type": "tool_use",
                                "id": tc.get("id", ""),
                                "name": func.get("name", ""),
                                "input": json.loads(func.get("arguments", "{}")),
                            }
                        )
                    converted.append({"role": "assistant", "content": blocks})
                else:
                    blocks = AnthropicAdapter._convert_content_to_blocks(content)
                    converted.append({"role": "assistant", "content": blocks})

            elif role == "tool":
                tc_id = msg.get("tool_call_id", "")
                if isinstance(content, list):
                    result_text = "".join(
                        item.get("text", "")
                        for item in content
                        if item.get("type") == "text"
                    )
                else:
                    result_text = content or ""
                temp_tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tc_id,
                        "content": result_text,
                    }
                )
        flush_tool_results()
        return converted

    @staticmethod
    def _convert_tools(
        internal_tools: list[ToolFunctionSchema],
    ) -> list[ToolUnionParam]:
        """Convert internal ToolFunctionSchema list to Anthropic tool definitions"""
        anthropic_tools = []
        for tool in internal_tools:
            func = tool.function
            anthropic_tool = {
                "name": func.name,
                "description": func.description,
                "input_schema": func.parameters.model_dump(exclude_none=True),
                "strict": tool.strict,
            }
            anthropic_tools.append(anthropic_tool)
        return anthropic_tools

    @staticmethod
    def _convert_tool_choice(choice: ToolChoice | None) -> ToolChoiceParam:
        """Convert internal ToolChoice to Anthropic tool_choice parameter"""
        if choice is None or choice == "auto":
            return {"type": "auto"}
        elif choice == "none":
            return {"type": "none"}
        elif choice == "required":
            return {"type": "any"}
        elif isinstance(choice, ToolFunctionSchema):
            return {
                "type": "tool",
                "name": choice.function.name,
            }
        raise ValueError(f"Invalid choice: {choice}")

    @override
    async def call_api(
        self, messages: Iterable, *args, **kwargs
    ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
        """Plain text generation (no tool calls)"""
        preset: ModelPreset = self.preset
        preset_config: ModelConfig = preset.config
        config: AmritaConfig = self.config
        client = anthropic.AsyncAnthropic(
            api_key=preset.api_key,
            base_url=preset.base_url,
            timeout=config.llm.llm_timeout,
            max_retries=config.llm.max_retries,
        )

        internal_msgs = list(messages)
        anthropic_msgs: list[MessageParam] = self._convert_messages(internal_msgs)

        stream = preset_config.stream
        text_resp = StringIO()

        if stream:
            async with client.messages.stream(
                model=preset.model,
                messages=anthropic_msgs,
                max_tokens=config.llm.max_tokens,
                top_p=preset_config.top_p,
                temperature=preset_config.temperature,
            ) as resp:
                async for chunk in resp.text_stream:
                    text_resp.write(chunk)
                    yield chunk
                last_msg = await resp.get_final_message()
                usage: UniResponseUsage[int] = UniResponseUsage[int](
                    prompt_tokens=last_msg.usage.input_tokens,
                    completion_tokens=last_msg.usage.output_tokens,
                    total_tokens=last_msg.usage.input_tokens
                    + last_msg.usage.output_tokens,
                )
        else:
            last_msg = await client.messages.create(
                model=preset.model,
                messages=anthropic_msgs,
                max_tokens=config.llm.max_tokens,
                top_p=preset_config.top_p,
                temperature=preset_config.temperature,
            )
            for ct in last_msg.content:
                if isinstance(ct, TextBlock):
                    text_resp.write(ct.text)
            usage = UniResponseUsage[int](
                prompt_tokens=last_msg.usage.input_tokens,
                completion_tokens=last_msg.usage.output_tokens,
                total_tokens=last_msg.usage.input_tokens + last_msg.usage.output_tokens,
            )

        yield UniResponse(
            content=text_resp.getvalue(),
            usage=usage,
            tool_calls=None,
        )

    @override
    async def call_tools(
        self,
        messages: Iterable,
        tools: list[ToolFunctionSchema],
        tool_choice: ToolChoice | None = None,
    ) -> UniResponse[None, list[ToolCall] | None]:
        """Tool call specific interface; returns tool_calls in UniResponse"""
        preset: ModelPreset = self.preset
        preset_config: ModelConfig = preset.config
        config: AmritaConfig = self.config
        client = anthropic.AsyncAnthropic(
            api_key=preset.api_key,
            base_url=preset.base_url,
            timeout=config.llm.llm_timeout,
            max_retries=config.llm.max_retries,
        )

        internal_msgs = list(messages)
        anthropic_msgs: list[MessageParam] = self._convert_messages(internal_msgs)
        anthropic_tools: list[ToolUnionParam] = self._convert_tools(tools)
        anthropic_tool_choice: (
            ToolChoiceAutoParam
            | ToolChoiceAnyParam
            | ToolChoiceToolParam
            | ToolChoiceNoneParam
        ) = self._convert_tool_choice(tool_choice)

        response = await client.messages.create(
            model=preset.model,
            messages=anthropic_msgs,
            max_tokens=config.llm.max_tokens,
            top_p=preset_config.top_p,
            temperature=preset_config.temperature,
            tools=anthropic_tools,
            tool_choice=anthropic_tool_choice,
        )

        tool_calls = []
        if response.stop_reason == "tool_use":
            tool_calls.extend(
                [
                    ToolCall(
                        id=block.id,
                        type="function",
                        function=Function(
                            name=block.name,
                            arguments=json.dumps(block.input, ensure_ascii=False),
                        ),
                    )
                    for block in response.content
                    if isinstance(block, ToolUseBlock)
                ]
            )
        return UniResponse(
            role="assistant",
            content=None,
            tool_calls=tool_calls if tool_calls else None,
        )

    @staticmethod
    def get_adapter_protocol() -> tuple[str, str]:
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
