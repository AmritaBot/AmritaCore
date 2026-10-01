from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field

from amrita_core.types.base import BaseModel
from amrita_core.types.billing import RateConfig

if TYPE_CHECKING:
    from amrita_core.config import AmritaConfig


class ModelConfig(BaseModel):
    """Model configuration"""

    top_k: int = Field(
        default=50,
        description="TopK (Some model adapters may not support this parameter)",
    )
    top_p: float = Field(default=0.8, description="TopP")
    temperature: float = Field(default=0.6, description="Temperature")
    stream: bool = Field(
        default=False,
        description="Whether to enable streaming response (output by character)",
    )
    multimodal: bool = Field(
        default=False,
        description="Whether to support multimodal input (e.g. image recognition)",
    )
    cot_model: bool = Field(
        default=False,
        description="Whether to remove the `<think>` tag in the response",
    )


class ThinkingConfig(
    BaseModel
):  # TODO: use model-adapter specific config like the structure of `Content`.
    """Thinking/reasoning configuration for a model preset."""

    thinking_type: Literal["enabled", "disabled"] | None = Field(
        default=None,
        description="Add `thinking.type` property in request (if provider supported, it's provider specificed)",
    )
    enable_thinking: bool | None = Field(
        default=None,
        description="Whether to enable thinking/reasoning (add `enable_thinking` property in request, it's provider specificed)",
    )
    thinking_effort: str | None = Field(
        default="high",
        description="Thinking effort level (model-dependent, normally are `minimal`,`low`,`medium`, `high`, `xhigh` or `max`. )",
    )
    content_mode: Literal["never", "by-tool", "optional"] = Field(
        default="optional",
        description=(
            "How to handle reasoning_content: "
            "never=strip all, by-tool=keep only for assistants with tool_calls, "
            "optional=pass through"
        ),
    )


class ModelPreset(BaseModel):
    model: str = Field(
        default="auto", description="Name of the AI model to use (e.g. gpt-3.5-turbo)"
    )
    name: str = Field(
        default="default", description="Identifier name for current preset"
    )
    base_url: str = Field(
        default="",
        description="Base address of API service (use OpenAI default if empty)",
    )
    api_key: str = Field(default="", description="Key required to access API")
    protocol: str = Field(default="__main__", description="Protocol adapter type")
    rate: RateConfig | None = Field(
        default=None,
        description="Pricing snapshot used for cost accounting (optional)",
    )
    max_context: int | None = Field(
        default=None,
        ge=1,
        description="Input token budget of the model. Together with `max_output` "
        "it forms the attention window. Falls back to "
        "`config.llm.session_tokens_windows` when unset.",
    )
    max_output: int | None = Field(
        default=None,
        ge=1,
        description="Tokens reserved for the response. Falls back to "
        "`config.llm.max_tokens` when unset.",
    )
    config: ModelConfig = Field(
        default_factory=ModelConfig, description="Model configuration"
    )
    thinking_config: ThinkingConfig | None = Field(
        default=None,
        description="Thinking/reasoning configuration for the model preset(If adapter supported)",
    )
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: Path):
        if path.exists():
            with path.open(
                "r",
                encoding="utf-8",
            ) as f:
                data = json.load(f)
            return cls.model_validate(data)
        return cls()  # Return default values

    def save(self, path: Path):
        with path.open("w", encoding="u8") as f:
            json.dump(self.model_dump(mode="json"), f, indent=4, ensure_ascii=False)


def resolve_max_context(preset: ModelPreset, config: AmritaConfig) -> int:
    """Effective input token budget: preset value, else the config default."""
    if preset.max_context is not None:
        return preset.max_context
    return config.llm.session_tokens_windows


def resolve_max_output(preset: ModelPreset, config: AmritaConfig) -> int:
    """Effective response reservation: preset value, else the config default."""
    if preset.max_output is not None:
        return preset.max_output
    return config.llm.max_tokens
