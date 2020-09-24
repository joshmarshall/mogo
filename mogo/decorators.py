"""
Just various decorators.
"""

from typing import Any, cast, Callable, Optional, Type, TypeVar, Union


T = TypeVar("T")


class notinstancemethod(object):
    """
    Used to refuse access to a classmethod if called from an instance.
    """

    def __init__(self, func: Union[Callable[..., T], classmethod]) -> None:
        if type(func) is not classmethod:
            raise ValueError("`notinstancemethod` called on non-classmethod")
        self.func = func

    def __get__(
            self, obj: Any,
            objtype: Optional[Type[Any]] = None) -> Callable[..., T]:
        if obj is not None:
            raise TypeError("Cannot call this method on an instance.")
        return cast(classmethod, self.func).__get__(obj, objtype)
