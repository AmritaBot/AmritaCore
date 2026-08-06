from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from amrita_core.types import USER_INPUT, SendMessageWrap

if TYPE_CHECKING:
    from amrita_sense.streaming import SuspendObjectStream

    from amrita_core.chatmanager import ChatObject
    from amrita_core.config import AmritaConfig
    from amrita_core.tools.manager import MultiToolsManager
    from amrita_core.types.preset import ModelPreset
    from amrita_core.types.response import UniResponseUsage


def build_strategy_context(
    *,
    user_input: USER_INPUT,
    original_context: SendMessageWrap,
    chat_object: ChatObject | None = None,
    preset: ModelPreset | None = None,
    config: AmritaConfig | None = None,
    tools_manager: MultiToolsManager | None = None,
    io_stream: SuspendObjectStream | None = None,
    train_content: str | None = None,
    stream_id: str | None = None,
    resp_extra_usage: UniResponseUsage | None = None,
) -> StrategyContext:
    """Build a ``StrategyContext`` with both legacy and DI resource fields.

    This is the **single factory** for all ``StrategyContext`` construction.
    When a new DI field is added to ``StrategyContext``, update this function
    and both ``_run_strategy`` and ``STRATEGY_INIT`` will pick it up.
    """
    return StrategyContext(
        user_input=user_input,
        original_context=original_context,
        chat_object=chat_object,
        preset=preset,
        config=config,
        tools_manager=tools_manager,
        io_stream=io_stream,
        train_content=train_content,
        stream_id=stream_id,
        resp_extra_usage=resp_extra_usage,
    )


@dataclass
class StrategyContext:
    """Execution context passed to agent strategies.

    Holds both the original message context and the DI resources that strategies
    need at runtime.  ``chat_object`` is the lifecycle-manager handle for the
    current conversation (the core unit of a dialogue); the DI resource fields
    below are the preferred way to reach individual resources, falling back to
    ``chat_object`` when a resource is not injected.
    """

    user_input: USER_INPUT
    original_context: SendMessageWrap

    # Lifecycle-manager handle for the current conversation (core unit).
    chat_object: ChatObject | None = None

    # DI resource fields (preferred path)
    preset: ModelPreset | None = None
    config: AmritaConfig | None = None
    tools_manager: MultiToolsManager | None = None
    io_stream: SuspendObjectStream | None = None
    train_content: str | None = None
    stream_id: str | None = None
    resp_extra_usage: UniResponseUsage | None = None

    # Properties / accessors

    @property
    def message(self) -> SendMessageWrap:
        return self.original_context

    @message.setter
    def message(self, value: SendMessageWrap):
        if not isinstance(value, SendMessageWrap):
            raise TypeError("message must be of type SendMessageWrap")
        self.original_context = value

    def get_original_context(self) -> SendMessageWrap:
        return self.original_context

    def get_user_input(self) -> USER_INPUT:
        return self.user_input
