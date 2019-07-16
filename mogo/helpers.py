from typing import Optional, TypeVar


T = TypeVar("T")


def check_none(value: Optional[T]) -> T:
    if value is None:
        raise ValueError("Value is unexpectedly None.")
    return value
