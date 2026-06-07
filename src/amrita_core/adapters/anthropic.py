import json
from collections.abc import AsyncGenerator, Iterable
from io import StringIO

from amrita_sense.logging import logger
from pydantic import BaseModel, Field
from typing_extensions import override

from amrita_core.config import AmritaConfig
from amrita_core.contents import MessageMetadataPayload, MessageWithMetadata
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


try:
    import anthropic
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

    class AnthropicAdapter(ModelAdapter):
        """Anthropic Protocol Adapter"""

        @staticmethod
        def _convert_content_to_blocks(
            content: str | list[dict] | None,
        ) -> list[dict]:
            """Convert internal content to Anthropic content blocks"""
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
                    blocks = []
                    # thinking block must come before text/tool_use blocks
                    if msg.get("reasoning_content") and msg.get("reasoning_signature"):
                        blocks.append(
                            {
                                "type": "thinking",
                                "thinking": msg["reasoning_content"],
                                "signature": msg["reasoning_signature"],
                            }
                        )
                    if tool_calls:
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
                    else:
                        blocks.extend(
                            AnthropicAdapter._convert_content_to_blocks(content)
                        )
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
            self, messages: Iterable, **kwargs
        ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
            """Plain text generation (no tool calls)"""
            preset: ModelPreset = self.preset
            preset_config: ModelConfig = preset.config
            config: AmritaConfig = self.config
            if (
                preset.thinking_config
                and preset.thinking_config.thinking_type == "enabled"
            ):
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": int(
                        preset.thinking_config.thinking_effort or 1024
                    ),
                }
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
            reasoning = ""
            reasoning_signature = ""

            if stream:
                async with client.messages.stream(
                    model=preset.model,
                    messages=anthropic_msgs,
                    max_tokens=config.llm.max_tokens,
                    top_p=preset_config.top_p,
                    temperature=preset_config.temperature,
                    **kwargs,
                ) as resp:
                    async for event in resp:
                        if event.type == "thinking_delta":
                            reasoning += event.thinking
                            yield MessageWithMetadata(
                                content=event.thinking,
                                metadata=MessageMetadataPayload(
                                    type="reasoning_chunk",
                                    extra_type="thinking_delta",
                                ),
                            )
                        elif event.type == "signature_delta":
                            reasoning_signature += event.signature
                        elif event.type == "text_delta":
                            text_resp.write(event.text)
                            yield event.text
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
                    **kwargs,
                )
                for ct in last_msg.content:
                    if isinstance(ct, TextBlock):
                        text_resp.write(ct.text)
                    elif hasattr(ct, "thinking"):
                        reasoning += ct.thinking
                        if hasattr(ct, "signature"):
                            reasoning_signature = ct.signature
                        yield MessageWithMetadata(
                            content=ct.thinking,
                            metadata=MessageMetadataPayload(
                                type="reasoning_chunk", extra_type="thinking"
                            ),
                        )
                usage = UniResponseUsage[int](
                    prompt_tokens=last_msg.usage.input_tokens,
                    completion_tokens=last_msg.usage.output_tokens,
                    total_tokens=last_msg.usage.input_tokens
                    + last_msg.usage.output_tokens,
                )
                text_content = text_resp.getvalue()
                yield text_content

            yield UniResponse(
                content=text_resp.getvalue(),
                usage=usage,
                tool_calls=None,
                reasoning_content=reasoning or None,
                reasoning_signature=reasoning_signature or None,
            )

        @override
        async def call_tools(
            self,
            messages: Iterable,
            tools: list[ToolFunctionSchema],
            tool_choice: ToolChoice | None = None,
            **kwargs,
        ) -> UniResponse[None, list[ToolCall] | None]:
            """Tool call specific interface; returns tool_calls in UniResponse"""
            preset: ModelPreset = self.preset
            preset_config: ModelConfig = preset.config
            config: AmritaConfig = self.config
            if (
                preset.thinking_config
                and preset.thinking_config.thinking_type == "enabled"
            ):
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": int(
                        preset.thinking_config.thinking_effort or 1024
                    ),
                }
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
                **kwargs,
            )

            usage = None
            if getattr(response, "usage", None) is not None:
                usage = UniResponseUsage[int](
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens
                    + response.usage.output_tokens,
                )

            tool_calls = []
            reasoning = ""
            reasoning_signature = ""
            for block in response.content:
                if isinstance(block, ToolUseBlock):
                    tool_calls.append(
                        ToolCall(
                            id=block.id,
                            type="function",
                            function=Function(
                                name=block.name,
                                arguments=json.dumps(block.input, ensure_ascii=False),
                            ),
                        )
                    )
                elif hasattr(block, "thinking"):
                    reasoning += block.thinking
                    if hasattr(block, "signature"):
                        reasoning_signature = block.signature
            return UniResponse(
                role="assistant",
                content=None,
                tool_calls=tool_calls if tool_calls else None,
                usage=usage,
                reasoning_content=reasoning or None,
                reasoning_signature=reasoning_signature or None,
            )

        @staticmethod
        def get_adapter_protocol() -> tuple[str, str]:
            return ("anthropic", "claude")

    __all__ = ["AnthropicAdapter", "AnthropicFunctionSchema"]
except ImportError:
    logger.info(
        "Anthropic SDK not found. Install it by `amrita_core[anthropic]` AnthropicAdapter will not be available."
    )
    __all__ = ["AnthropicFunctionSchema"]
