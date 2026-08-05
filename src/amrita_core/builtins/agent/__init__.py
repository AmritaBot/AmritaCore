"""Built-in ReAct agent strategies.

This package was split from the original monolithic ``builtins/agent.py``:

- ``react_base`` — :class:`BaseReActAgentStrategy`, :class:`NoActionAgentStrategy`
  and shared helpers.
- ``react_hyb`` — :class:`HybridReActAgentStrategy` (deprecated; kept for
  backward compatibility only).
- ``react_comm`` — :class:`ReActAgentStrategy` (the regular/common
  implementation) and the :data:`AmritaAgentStrategy` alias.
"""

from ..tools import PROCESS_MESSAGE
from .react_base import BaseReActAgentStrategy, NoActionAgentStrategy
from .react_comm import AmritaAgentStrategy, ReActAgentStrategy
from .react_hyb import HybridReActAgentStrategy

__all__ = [
    "PROCESS_MESSAGE",
    "AmritaAgentStrategy",
    "BaseReActAgentStrategy",
    "HybridReActAgentStrategy",
    "NoActionAgentStrategy",
    "ReActAgentStrategy",
]
