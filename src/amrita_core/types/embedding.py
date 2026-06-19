from __future__ import annotations

from collections.abc import Sequence

from amrita_core.types.base import BaseModel


class EmbeddingChunk(BaseModel):
    """Represents an embedding vector returned by embedding adapter."""

    embedding: Sequence[float]

    index: int
