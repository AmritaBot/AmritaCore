from __future__ import annotations

import time

from pydantic import ConfigDict, Field

from amrita_core.types.base import DirtyAwareBaseModel
from amrita_core.types.billing import BillingRecord
from amrita_core.types.message import CONTENT_LIST_TYPE_ITEM
from amrita_core.types.response import UniResponseUsage


class MemoryModel(DirtyAwareBaseModel):
    dirty_exclude__: tuple[str, ...] = ("model_config",)
    model_config = ConfigDict(extra="allow")
    messages: list[CONTENT_LIST_TYPE_ITEM] = Field(default_factory=list)
    time: float = Field(default_factory=time.time, description="Timestamp")
    abstract: str = Field(default="", description="Summary")
    usage: UniResponseUsage | None = Field(
        default=None,
        description="Usage of the most recent provider request over this context",
    )
    billing: list[BillingRecord] = Field(
        default_factory=list,
        description="Per-request billing records accumulated over this context",
    )
