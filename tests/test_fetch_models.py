"""`fetch_models`: the capability flag and the per-adapter model listing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from amrita_core.adapters.anthropic import AnthropicAdapter
from amrita_core.adapters.openai import OpenAIAdapter
from amrita_core.adapters.openai_responses import OpenAIResponsesAdapter
from amrita_core.base.adapter import FeatureFlag, ModelAdapter
from amrita_core.types import ModelInfo, ModelPreset


def _preset(protocol: str, base_url: str = "https://api.example.com") -> ModelPreset:
    return ModelPreset(
        model="m", name="p", api_key="k", protocol=protocol, base_url=base_url
    )


def _page(*entries: dict) -> SimpleNamespace:
    return SimpleNamespace(
        data=[SimpleNamespace(model_dump=lambda e=e: e) for e in entries]
    )


class TestFeatureFlag:
    def test_defaults_to_closed(self):
        assert FeatureFlag().fetch_models is False

    def test_builtins_declare_it(self):
        assert OpenAIAdapter.features.fetch_models is True
        assert AnthropicAdapter.features.fetch_models is True
        assert OpenAIResponsesAdapter.features.fetch_models is True


class TestBaseAdapter:
    @pytest.mark.asyncio
    async def test_default_raises(self):
        class NoCatalogue(ModelAdapter):
            __no_register__ = True
            __abstract__ = True

        with pytest.raises(NotImplementedError):
            await NoCatalogue.fetch_models(_preset("nope"))


class TestOpenAIListing:
    @pytest.mark.asyncio
    async def test_maps_the_model_page(self):
        page = _page(
            {
                "id": "deepseek-flash",
                "object": "model",
                "owned_by": "deepseek",
                "name": "DeepSeek-V4.1-Flash",
                "context_window": 1048576,
                "input_modalities": ["text", "image"],
            }
        )
        client = SimpleNamespace(
            models=SimpleNamespace(list=AsyncMock(return_value=page))
        )
        with patch(
            "amrita_core.adapters.openai.openai.AsyncOpenAI", return_value=client
        ):
            models = await OpenAIAdapter.fetch_models(_preset("openai"))

        assert models == [
            ModelInfo(
                id="deepseek-flash",
                object="model",
                owned_by="deepseek",
                name="DeepSeek-V4.1-Flash",
                context_window=1048576,
                input_modalities=["text", "image"],
            )
        ]
        # A class method needs only the preset.
        assert isinstance(models[0], ModelInfo)


class TestResponsesListing:
    @pytest.mark.asyncio
    async def test_uses_the_same_models_endpoint(self):
        page = _page({"id": "gpt-5", "owned_by": "openai"})
        client = SimpleNamespace(
            models=SimpleNamespace(list=AsyncMock(return_value=page))
        )
        with patch(
            "amrita_core.adapters.openai_responses.openai.AsyncOpenAI",
            return_value=client,
        ):
            models = await OpenAIResponsesAdapter.fetch_models(
                _preset("openai-responses")
            )
        assert [m.id for m in models] == ["gpt-5"]


class TestAnthropicListing:
    @pytest.mark.asyncio
    async def test_maps_display_name(self):
        page = SimpleNamespace(
            data=[
                SimpleNamespace(
                    id="claude-x",
                    display_name="Claude X",
                    created_at="2026-01-01T00:00:00Z",
                )
            ]
        )
        client = SimpleNamespace(
            models=SimpleNamespace(list=AsyncMock(return_value=page))
        )
        with patch(
            "amrita_core.adapters.anthropic.anthropic.AsyncAnthropic",
            return_value=client,
        ):
            models = await AnthropicAdapter.fetch_models(_preset("anthropic"))

        assert models[0].id == "claude-x"
        assert models[0].name == "Claude X"
        assert models[0].created_at == "2026-01-01T00:00:00Z"
