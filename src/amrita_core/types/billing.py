"""Billing records for provider requests.

AmritaCore collects the raw material needed for cost accounting but does not
compute currency amounts itself: each record carries the token counts plus a
snapshot of the pricing that applied at request time. Consumers (dashboards,
quota enforcers, billing pipelines) derive the money value from ``rate`` and
the token counts, so a later price change never rewrites history.
"""

from __future__ import annotations

import time
from decimal import Decimal

from pydantic import Field

from amrita_core.types.base import BaseModel


class RateConfig(BaseModel):
    """Unit price snapshot for a model.

    ``input`` and ``output`` are prices per ``per`` tokens, expressed in
    ``currency``. ``Decimal`` is used so consumers can multiply by token
    counts without accumulating binary floating point error.
    """

    per: int = Field(default=1000, gt=0, description="Token bundle the prices refer to")
    input: Decimal = Field(default=Decimal("0"), description="Price per `per` input tokens")
    output: Decimal = Field(
        default=Decimal("0"), description="Price per `per` output tokens"
    )
    currency: str = Field(default="USD", description="Currency code of the prices")


class BillingRecord(BaseModel):
    """One provider request's usage and pricing snapshot.

    Granularity is a single request: every completion or tool-calling round
    that reaches the provider produces at most one record. ``model``,
    ``preset_name`` and ``rate`` are stored alongside the counts so a record
    stays self-describing after presets or prices change.
    """

    model: str | None = Field(default=None, description="Model name used for the request")
    preset_name: str | None = Field(
        default=None, description="Preset name the request was issued with"
    )
    rate: RateConfig | None = Field(
        default=None, description="Pricing snapshot captured at request time"
    )

    prompt_tokens: int = Field(default=0, description="Prompt tokens reported")
    completion_tokens: int = Field(default=0, description="Completion tokens reported")
    total_tokens: int = Field(default=0, description="Total tokens reported")
    cache_hit: int | None = Field(default=None, description="Tokens read from cache")
    cache_creation: int | None = Field(
        default=None, description="Tokens spent creating cache entries"
    )

    session_id: str = Field(default="", description="Owning session id")
    stream_id: str = Field(default="", description="Owning run id")
    request_id: str | None = Field(default=None, description="Provider request id")
    ts: float = Field(default_factory=time.time, description="Record timestamp")


__all__ = ["BillingRecord", "RateConfig"]
