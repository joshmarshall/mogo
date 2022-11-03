"""
Just various decorators.
"""

from typing import Any, cast, Callable, Generic, Optional, Type, TypeVar


T = TypeVar("T")


class notinstancemethod(Generic[T]):
    """
    Used to refuse access to a classmethod if called from an instance.
    """

    def __init__(self, func: Callable[..., T]) -> None:
        # Using string check instead of actual type so we don't overwrite
        # the inferred return type T of the callable / classmethod
        if not str(type(func)) == "<class 'classmethod'>":
            raise ValueError("`notinstancemethod` called on non-classmethod")
        self.func = func

    def __get__(
            self, obj: Any,
            objtype: Optional[Type[Any]] = None) -> Callable[..., T]:
        if obj is not None:
            raise TypeError("Cannot call this method on an instance.")
        return cast(Callable[..., T], self.func.__get__(obj, objtype))
