from dataclasses import dataclass
from typing import TYPE_CHECKING

from amrita_core.types import USER_INPUT, SendMessageWrap

if TYPE_CHECKING:
    from amrita_core.chatmanager import ChatObject


@dataclass
class StrategyContext:
    user_input: USER_INPUT
    original_context: SendMessageWrap
    chat_object: "ChatObject"

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
