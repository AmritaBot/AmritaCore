"""OpenAI Responses API adapter (``/v1/responses``).

Stateless by design: every request carries the whole conversation as ``input``
items and ``store`` is pinned to ``False``. Nothing depends on server-side
response objects, so the adapter behaves the same against OpenAI, Azure-style
proxies and the OpenAI-compatible vendors that implement ``/responses``
without conversation storage.

Two shapes differ from Chat Completions and are the reason this adapter exists:

- tool results travel as ``function_call_output`` items whose ``output`` may be
  a list of ``input_text`` / ``input_image`` / ``input_file`` parts, so a tool
  can hand an image back to the model directly;
- tool calls are separate ``function_call`` items rather than fields on an
  assistant message, and text arrives as ``output_text`` parts.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Iterable, Sequence
from typing import Any, Literal, cast

import openai
from amrita_sense.logging import debug_log
from typing_extensions import override

from amrita_core.base.adapter import (
    AGENTIC_RETURNING,
    COMPLETION_RETURNING,
    FeatureFlag,
    ModelAdapter,
)
from amrita_core.config import AmritaConfig
from amrita_core.contents import MessageMetadataPayload, MessageWithMetadata
from amrita_core.exceptions import (
    AdapterResponseError,
    normalize_adapter_errors,
)
from amrita_core.tools.models import ToolChoice, ToolFunctionSchema
from amrita_core.types import (
    EmbeddingChunk,
    Function,
    ModelConfig,
    ModelInfo,
    ModelPreset,
    ToolCall,
    UniResponse,
    UniResponseUsage,
)
from amrita_core.types.preset import resolve_max_output
from amrita_core.types.response import STOP_REASON, RequestMetadata
from amrita_core.types.tool import block_label_of_type, degraded_block_note
from amrita_core.utils import model_dump

# For Responses `input_image` detail levels, `original` isn't accepted by every vendor, so it's forwarded only when requested.
_IMAGE_DETAILS = {"auto", "low", "high", "original"}


def _content_parts(content: Any, *, assistant: bool = False) -> list[dict[str, Any]]:
    """Convert internal content into Responses content parts.

    ``assistant`` messages use ``output_text``; every other role uses
    ``input_text``. Non-text blocks the assistant turn cannot carry (images in a
    historical answer) fall back to the same placeholder wording the gateway
    uses, so the model is told what is missing instead of reading a silently
    shortened answer.
    """
    text_type = "output_text" if assistant else "input_text"
    if content is None:
        return []
    if isinstance(content, str):
        return [{"type": text_type, "text": content}] if content else []
    parts: list[dict[str, Any]] = []
    for item in content:
        if isinstance(item, str):
            parts.append({"type": text_type, "text": item})
            continue
        item_type = item.get("type") if isinstance(item, dict) else None
        if item_type == "text":
            parts.append({"type": text_type, "text": str(item.get("text") or "")})
        elif item_type == "image_url" and not assistant:
            raw = item.get("image_url")
            if isinstance(raw, dict):
                url, detail = raw.get("url"), raw.get("detail")
            else:
                url, detail = raw, None
            if url:
                image_part: dict[str, Any] = {
                    "type": "input_image",
                    "image_url": str(url),
                }
                if isinstance(detail, str) and detail in _IMAGE_DETAILS:
                    image_part["detail"] = detail
                parts.append(image_part)
        elif item_type == "file" and not assistant:
            raw = item.get("file")
            file_part: dict[str, Any] | None = None
            if isinstance(raw, dict):
                if raw.get("file_id"):
                    file_part = {"type": "input_file", "file_id": str(raw["file_id"])}
                elif raw.get("file_data"):
                    file_part = {
                        "type": "input_file",
                        "file_data": str(raw["file_data"]),
                    }
                    if filename := raw.get("filename"):
                        file_part["filename"] = str(filename)
            if file_part is not None:
                parts.append(file_part)
        else:
            parts.append(
                {
                    "type": text_type,
                    "text": degraded_block_note(block_label_of_type(str(item_type))),
                }
            )
    return parts or ([] if assistant else [{"type": text_type, "text": ""}])


def _tool_output(content: Any) -> str | list[dict[str, Any]]:
    """``function_call_output.output``: plain text, or a part list.

    A string is passed through unchanged - providers treat it as one text part,
    and keeping it a string avoids reserializing large plain-text results.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return _content_parts(content)


def _reasoning_items_from(signature: str | None) -> list[dict[str, Any]]:
    """Read back the reasoning items stored on an assistant message.

    Some providers reject a follow-up whose earlier tool-calling turn lacks the
    reasoning items that produced it, even when thinking looks off.
    The items cannot be rebuilt from the text alone — they carry an ``id`` and
    ``encrypted_content`` — so the adapter parks them on ``reasoning_signature``
    (a string field every adapter may use for round-trip state) and replays them
    verbatim. A plain Anthropic signature is not JSON, so it is ignored here.
    """
    if not signature or not signature.startswith("{"):
        return []
    try:
        payload = json.loads(signature)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, dict) or payload.get("provider") != "openai-responses":
        return []
    items = payload.get("items")
    return items if isinstance(items, list) else []


def _reasoning_signature(items: list[dict[str, Any]]) -> str | None:
    """Serialize reasoning items for the next turn, or ``None`` if none arrived."""
    if not items:
        return None
    return json.dumps(
        {"provider": "openai-responses", "items": items}, ensure_ascii=False
    )


def _to_input_items(messages: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate the internal message list into Responses ``input`` items.

    Order matters: a historical assistant turn becomes its ``message`` item (when
    it has text) followed by one ``function_call`` item per call, and each tool
    result becomes a ``function_call_output`` keyed by ``call_id``. Splitting the
    calls out of the message is what lets the pairing survive a round trip.
    """
    items: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "tool":
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": msg.get("tool_call_id", ""),
                    "output": _tool_output(content),
                }
            )
        elif role == "assistant":
            for stored in _reasoning_items_from(msg.get("reasoning_signature")):
                item: dict[str, Any] = {
                    "type": "reasoning",
                    "id": stored.get("id", ""),
                    "summary": [],
                }
                if stored.get("text"):
                    item["content"] = [
                        {"type": "reasoning_text", "text": stored["text"]}
                    ]
                if stored.get("encrypted_content"):
                    item["encrypted_content"] = stored["encrypted_content"]
                items.append(item)
            parts = _content_parts(content, assistant=True)
            if parts:
                items.append({"type": "message", "role": "assistant", "content": parts})
            for call in msg.get("tool_calls") or []:
                call = call if isinstance(call, dict) else call.model_dump()
                function = call.get("function") or {}
                items.append(
                    {
                        "type": "function_call",
                        "call_id": call.get("id", ""),
                        "name": function.get("name", ""),
                        "arguments": function.get("arguments", "") or "{}",
                    }
                )
        elif role in ("system", "user", "developer"):
            items.append(
                {
                    "type": "message",
                    "role": role,
                    "content": _content_parts(content),
                }
            )
    return items


def _to_tools(tools: Sequence[ToolFunctionSchema]) -> list[dict[str, Any]]:
    """Flatten the internal tool schema into the Responses tool shape.

    Responses keeps ``name`` / ``parameters`` at the top level of the tool
    object; the nested ``function`` object is the Chat Completions shape and is
    rejected outright.
    """
    converted: list[dict[str, Any]] = []
    for tool in tools:
        function = tool.function
        converted.append(
            {
                "type": "function",
                "name": function.name,
                "description": function.description,
                "parameters": function.parameters.model_dump(exclude_none=True),
                "strict": tool.strict,
            }
        )
    return converted


def _to_tool_choice(choice: ToolChoice | None) -> Any:
    """Translate the internal tool choice into the Responses shape."""
    if choice is None or choice == "auto":
        return "auto"
    if choice in ("none", "required"):
        return choice
    if isinstance(choice, ToolFunctionSchema):
        return {"type": "function", "name": choice.function.name}
    raise ValueError(f"Invalid tool choice: {choice!r}")


def _usage(usage: Any) -> UniResponseUsage | None:
    """Map ``ResponseUsage`` onto the framework's usage model."""
    if usage is None:
        return None
    details = getattr(usage, "input_tokens_details", None)
    return UniResponseUsage(
        prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
        completion_tokens=getattr(usage, "output_tokens", 0) or 0,
        total_tokens=getattr(usage, "total_tokens", 0) or 0,
        cache_hit=getattr(details, "cached_tokens", None),
    )


def _stop_reason(response: Any, has_tool_calls: bool) -> STOP_REASON:
    """Derive the framework stop reason from a Responses object."""
    status = getattr(response, "status", None)
    if status == "incomplete":
        return "max_tokens"
    return "tool_use" if has_tool_calls else "stop_sequence"


def _metadata(response: Any, has_tool_calls: bool) -> RequestMetadata:
    """Build request metadata; the response id is the only request id exposed."""
    return RequestMetadata(
        model=getattr(response, "model", "__NOT_GIVEN__"),
        original_request_id=getattr(response, "id", None),
        stop_sequence=None,
        stop_reason=_stop_reason(response, has_tool_calls),
    )


def _parse_output(
    output: Iterable[Any],
) -> tuple[str, str, list[ToolCall], list[dict[str, Any]]]:
    """Read text, reasoning, tool calls and reasoning items out of ``output``."""
    text_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    reasoning_items: list[dict[str, Any]] = []
    for item in output:
        item_type = getattr(item, "type", None)
        if item_type == "message":
            for part in getattr(item, "content", None) or []:
                part_type = getattr(part, "type", None)
                if part_type == "output_text":
                    text_parts.append(getattr(part, "text", "") or "")
                elif part_type == "refusal":
                    text_parts.append(getattr(part, "refusal", "") or "")
        elif item_type == "function_call":
            tool_calls.append(
                ToolCall(
                    id=getattr(item, "call_id", "") or "",
                    type="function",
                    function=Function(
                        name=getattr(item, "name", "") or "",
                        arguments=getattr(item, "arguments", "") or "{}",
                    ),
                )
            )
        elif item_type == "reasoning":
            text = "".join(
                getattr(part, "text", "") or ""
                for part in getattr(item, "content", None) or []
            )
            if not text:
                text = "".join(
                    getattr(summary, "text", "") or ""
                    for summary in getattr(item, "summary", None) or []
                )
            reasoning_parts.append(text)
            reasoning_items.append(
                {
                    "id": getattr(item, "id", "") or "",
                    "encrypted_content": getattr(item, "encrypted_content", None),
                    "text": text,
                }
            )
    return "".join(text_parts), "".join(reasoning_parts), tool_calls, reasoning_items


class OpenAIResponsesAdapter(ModelAdapter):
    """Adapter for the OpenAI Responses API, in stateless mode.

    Text, tool calls and multimodal tool results all ride the same request: the
    adapter declares ``tool_result_multimodal`` so the gateway never degrades a
    tool's image into a placeholder, and ``agentic_call`` so the agent loop can
    stream text while the calls are assembled.
    """

    __override__ = True
    features = FeatureFlag(
        agentic_call=True,
        input_multimodal=True,
        tool_result_multimodal=True,
        fetch_models=True,
    )

    def _client(self) -> openai.AsyncOpenAI:
        config: AmritaConfig = self.config
        preset: ModelPreset = self.preset
        return openai.AsyncOpenAI(
            base_url=preset.base_url,
            api_key=preset.api_key,
            timeout=config.llm.llm_timeout,
            max_retries=config.llm.max_retries,
        )

    def _request_kwargs(
        self,
        messages: Iterable[Any],
        tools: Sequence[ToolFunctionSchema] | None,
        tool_choice: ToolChoice | None,
        stream: bool,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Assemble one stateless request body.

        ``store=False`` and the absence of ``previous_response_id`` are the two
        invariants of stateless mode: the server keeps nothing between turns, so
        a retry or a preset fallback cannot resume someone else's conversation.
        """
        preset: ModelPreset = self.preset
        preset_config: ModelConfig = preset.config
        config: AmritaConfig = self.config

        request: dict[str, Any] = {
            "model": preset.model,
            "input": _to_input_items(model_dump(messages)),
            "max_output_tokens": resolve_max_output(preset, config),
            "top_p": preset_config.top_p,
            "temperature": preset_config.temperature,
            "stream": stream,
            "store": False,
        }
        if tools:
            request["tools"] = _to_tools(tools)
            request["tool_choice"] = _to_tool_choice(tool_choice)
        if preset.thinking_config is not None:
            reasoning: dict[str, str] = {}
            if preset.thinking_config.thinking_type == "disabled":
                # Responses turns thinking off via effort=none; an absent field keeps the default.
                reasoning["effort"] = "none"
            elif preset.thinking_config.thinking_type == "enabled":
                reasoning["effort"] = str(
                    preset.thinking_config.thinking_effort or "high"
                )
            elif preset.thinking_config.thinking_effort:
                reasoning["effort"] = str(preset.thinking_config.thinking_effort)
            if preset.thinking_config.enable_thinking:
                reasoning.setdefault("summary", "auto")
            if reasoning:
                request["reasoning"] = reasoning
        request.update(kwargs)
        return request

    @override
    @normalize_adapter_errors("openai-responses")
    async def call_api(
        self,
        messages: Iterable,
        stop: str | list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
        """Plain text generation; the Responses API has no stop-sequence field."""
        async for chunk in self._generate(messages, tools=None, **kwargs):
            yield cast(COMPLETION_RETURNING, chunk)

    @override
    @normalize_adapter_errors("openai-responses")
    async def agentic_call_api(
        self,
        messages: Iterable,
        tools: list[ToolFunctionSchema] | None = None,
        tool_choice: ToolChoice | None = None,
        stop: str | list[str] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[AGENTIC_RETURNING, None]:
        """Stream text and assemble tool calls from the same request."""
        async for chunk in self._generate(
            messages, tools=tools, tool_choice=tool_choice, **kwargs
        ):
            yield chunk

    @override
    @normalize_adapter_errors("openai-responses")
    async def call_tools(
        self,
        messages: Iterable,
        tools: list,
        tool_choice: ToolChoice | None = None,
        **kwargs: Any,
    ) -> UniResponse[str | None, list[ToolCall] | None]:
        """Non-streaming tool round, used by the legacy calling path."""
        client = self._client()
        request = self._request_kwargs(
            messages, tools, tool_choice, stream=False, **kwargs
        )
        response = await client.responses.create(**request)
        text, _, tool_calls, _ = _parse_output(response.output)
        return UniResponse(
            role="assistant",
            # A tool-calling turn may also speak; keep its output_text.
            content=text or None,
            tool_calls=tool_calls or None,
            usage=_usage(getattr(response, "usage", None)),
            metadata=_metadata(response, bool(tool_calls)),
        )

    @override
    async def call_embed(
        self, texts: Sequence[str], **kwargs: Any
    ) -> Sequence[EmbeddingChunk]:
        """The Responses API exposes no embedding endpoint."""
        raise NotImplementedError(
            "OpenAIResponsesAdapter does not support embeddings; use an"
            " `openai` or `anthropic` preset for `embed` work."
        )

    async def _generate(
        self,
        messages: Iterable,
        tools: Sequence[ToolFunctionSchema] | None = None,
        tool_choice: ToolChoice | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[AGENTIC_RETURNING, None]:
        """Run one request and yield text deltas plus the trailing ``UniResponse``."""
        preset: ModelPreset = self.preset
        client = self._client()
        stream = bool(preset.config.stream)
        request = self._request_kwargs(
            messages, tools, tool_choice, stream=stream, **kwargs
        )

        text = ""
        reasoning = ""
        usage: UniResponseUsage | None = None
        meta: RequestMetadata | None = None
        # output item id -> call slot; arguments arrive in fragments keyed by item id
        pending: dict[str, dict[str, Any]] = {}
        # reasoning items must be replayed verbatim on the next turn
        reasoning_items: list[dict[str, Any]] = []

        if stream:
            stream_resp = await client.responses.create(**request)
            async with stream_resp:
                async for event in stream_resp:
                    event_type = getattr(event, "type", "")
                    if event_type == "response.output_text.delta":
                        delta = getattr(event, "delta", "") or ""
                        text += delta
                        debug_log(delta)
                        yield delta
                    elif event_type in (
                        "response.reasoning_summary_text.delta",
                        "response.reasoning_text.delta",
                    ):
                        delta = getattr(event, "delta", "") or ""
                        reasoning += delta
                        yield MessageWithMetadata(
                            content=delta,
                            metadata=MessageMetadataPayload(
                                type="reasoning_chunk", extra_type="cot_chunk"
                            ),
                        )
                    elif event_type == "response.output_item.added":
                        item = getattr(event, "item", None)
                        if getattr(item, "type", None) == "function_call":
                            item_id = getattr(item, "id", "") or getattr(
                                item, "call_id", ""
                            )
                            pending[item_id] = {
                                "id": getattr(item, "call_id", None) or item_id,
                                "type": "function",
                                "function": {
                                    "name": getattr(item, "name", "") or "",
                                    "arguments": getattr(item, "arguments", "") or "",
                                },
                            }
                    elif event_type == "response.function_call_arguments.delta":
                        slot = pending.get(getattr(event, "item_id", ""))
                        if slot is not None:
                            slot["function"]["arguments"] += (
                                getattr(event, "delta", "") or ""
                            )
                    elif event_type == "response.output_item.done":
                        item = getattr(event, "item", None)
                        if getattr(item, "type", None) == "reasoning":
                            item_text = "".join(
                                getattr(part, "text", "") or ""
                                for part in getattr(item, "content", None) or []
                            )
                            reasoning_items.append(
                                {
                                    "id": getattr(item, "id", "") or "",
                                    "encrypted_content": getattr(
                                        item, "encrypted_content", None
                                    ),
                                    "text": item_text or reasoning,
                                }
                            )
                        elif getattr(item, "type", None) == "function_call":
                            item_id = getattr(item, "id", "") or getattr(
                                item, "call_id", ""
                            )
                            slot = pending.setdefault(
                                item_id,
                                {
                                    "id": getattr(item, "call_id", None) or item_id,
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                },
                            )
                            slot["id"] = getattr(item, "call_id", None) or slot["id"]
                            if name := getattr(item, "name", None):
                                slot["function"]["name"] = name
                            if arguments := getattr(item, "arguments", None):
                                # Trust the done event's full arguments over the fragments.
                                slot["function"]["arguments"] = arguments
                    elif event_type in ("response.completed", "response.incomplete"):
                        response = getattr(event, "response", None)
                        usage = _usage(getattr(response, "usage", None))
                        if not pending:
                            _, _, calls, parsed_items = _parse_output(
                                getattr(response, "output", None) or []
                            )
                            reasoning_items.extend(parsed_items)
                            for call in calls:
                                pending[call.id] = call.model_dump()
                        meta = _metadata(response, bool(pending))
                    elif event_type in ("response.failed", "error"):
                        response = getattr(event, "response", None)
                        error = getattr(response, "error", None) or getattr(
                            event, "message", None
                        )
                        raise AdapterResponseError(
                            f"Responses API reported a failure: {error}"
                        )
        else:
            response = await client.responses.create(**request)
            text, reasoning, calls, reasoning_items = _parse_output(response.output)
            if reasoning:
                yield MessageWithMetadata(
                    content=reasoning,
                    metadata=MessageMetadataPayload(
                        type="reasoning_chunk", extra_type="cot_chunk"
                    ),
                )
            if text:
                debug_log(text)
                yield text
            for call in calls:
                pending[call.id] = call.model_dump()
            usage = _usage(getattr(response, "usage", None))
            meta = _metadata(response, bool(pending))

        tool_calls: list[ToolCall] = []
        for slot in pending.values():
            if not slot.get("id"):
                slot["id"] = f"call_{len(tool_calls)}"
            tool_calls.append(ToolCall.model_validate(slot))

        yield UniResponse(
            role="assistant",
            content=text,
            usage=usage,
            tool_calls=cast(list[ToolCall], tool_calls) or None,
            reasoning_content=reasoning or None,
            reasoning_signature=_reasoning_signature(reasoning_items),
            metadata=meta or RequestMetadata(model=preset.model),
        )

    @classmethod
    @normalize_adapter_errors("openai-responses")
    async def fetch_models(cls, preset: ModelPreset) -> list[ModelInfo]:
        """List the models the endpoint advertises on ``/models``."""
        client = openai.AsyncOpenAI(
            base_url=preset.base_url,
            api_key=preset.api_key,
        )
        page = await client.models.list()
        return [ModelInfo.model_validate(item.model_dump()) for item in page.data]

    @staticmethod
    def get_adapter_protocol() -> str:
        return "openai-responses"

    @staticmethod
    def get_type() -> Literal["text-gen"]:
        return "text-gen"


__all__ = ["OpenAIResponsesAdapter"]
