from __future__ import annotations

from amrita_core.types.base import BaseModel


class ModelInfo(BaseModel, extra="allow"):
    """One entry from a provider's model list.

    Providers disagree on how much they describe a model: OpenAI returns
    ``id`` / ``created`` / ``owned_by``, Anthropic adds ``display_name``, and
    DeepSeek also reports context window, output limit and modalities. The
    optional fields cover what is commonly useful and ``extra="allow"`` keeps
    whatever else the provider sent instead of dropping it.
    """

    id: str
    name: str | None = None
    """Human-readable name, when the provider exposes one (Anthropic's ``display_name``)."""
    owned_by: str | None = None
    context_window: int | None = None
    max_output_tokens: int | None = None
    input_modalities: list[str] | None = None
    output_modalities: list[str] | None = None


__all__ = ["ModelInfo"]
