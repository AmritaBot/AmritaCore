from amrita_sense.hook.on import on_event

from .event import EventTypeEnum


def on_completion(priority: int = 10, block: bool = True):
    return on_event(EventTypeEnum.COMPLETION, priority, block)


def on_precompletion(priority: int = 10, block: bool = True):
    return on_event(EventTypeEnum.BEFORE_COMPLETION, priority, block)


def on_preset_fallback(priority: int = 10, block: bool = True):
    return on_event(EventTypeEnum.PRESET_FALLBACK, priority, block)
