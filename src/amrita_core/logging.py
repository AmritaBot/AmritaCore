from typing import Protocol


class ToStringAble(Protocol):
    def __str__(self) -> str: ...


debug: bool = False


def debug_log(message: ToStringAble) -> None:
    global debug
    if debug:
        print(message)
