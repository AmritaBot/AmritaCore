from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel as B_Model

from amrita_core.dirty import DirtyAwareModel


class BaseModel(B_Model):
    """BaseModel+dict duck typing"""

    def __str__(self) -> str:
        return json.dumps(self.model_dump(), ensure_ascii=True)

    def __repr__(self) -> str:
        return self.__str__()

    def __getitem__(self, key: str) -> Any:
        return self.model_dump()[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.__setattr__(key, value)


class DirtyAwareBaseModel(BaseModel, DirtyAwareModel): ...
