from .event import EventTypeEnum
from .matcher import Matcher


def on_completion(priority: int = 10, block: bool = True):
    return on_event(EventTypeEnum.COMPLETION, priority, block)


def on_precompletion(priority: int = 10, block: bool = True):
    return on_event(EventTypeEnum.BEFORE_COMPLETION, priority, block)


def on_event(event_type: EventTypeEnum | str, priority: int = 10, block: bool = True):
    return Matcher(event_type, priority, block)
