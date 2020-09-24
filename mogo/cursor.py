from mogo.helpers import check_none

from pymongo import ASCENDING, DESCENDING
from pymongo.collation import Collation
from pymongo.cursor import Cursor as PyCursor

from typing import Any, cast, Dict, Generic, Iterator, List, Optional, Tuple
from typing import Type, TypeVar, TYPE_CHECKING


ASC = ASCENDING
DESC = DESCENDING

T = TypeVar("T", bound="Model")


class Cursor(Generic[T]):
    """ A simple wrapper around pymongo's Cursor class. """

    _order_entries = []  # type: List[Tuple[str, int]]
    _query = None  # type: Optional[Dict[str, Any]]
    _model = None  # type: Optional[Type[T]]
    _model_class = None  # type: Optional[Type[T]]
    _cursor = None  # type: Optional[PyCursor]

    def __init__(
            self,
            model: Type[T],
            spec: Optional[Dict[str, Any]] = None,
            *args: Any,
            **kwargs: Any) -> None:
        self._order_entries = []
        self._query = spec
        self._model = model
        self._model_class = model
        self._cursor = PyCursor(
            self._model_class._get_collection(), spec, *args, **kwargs)

    def __iter__(self) -> "Cursor[T]":
        return self

    def __next__(self) -> T:
        value = check_none(self._cursor).next()
        return check_none(self._model)(**value)

    def next(self) -> T:
        # still need this, since pymongo's cursor still implements next()
        # and returns the raw dict.
        return self.__next__()

    def count(self) -> int:
        collection = check_none(self._model_class)._get_collection()
        if hasattr(collection, "count_documents"):
            return collection.count_documents(self._query or {})
        # count on a cursor is deprecated, ultimately this will be removed
        return check_none(self._cursor).count()

    # convenient because if it quacks like a list...
    def __len__(self) -> int:
        return self.count()

    def __getitem__(self, index: int) -> T:
        value = check_none(self._cursor).__getitem__(index)
        if isinstance(value, self.__class__):
            return cast(T, value)
        return check_none(self._model)(**value)

    def close(self) -> None:
        return check_none(self._cursor).close()

    def rewind(self) -> "Cursor[T]":
        check_none(self._cursor).rewind()
        return self

    def first(self) -> Optional[T]:
        if self.count() == 0:
            return None
        return self.next()

    def collation(self, collation: Collation) -> "Cursor[T]":
        check_none(self._cursor).collation(collation)
        return self

    def skip(self, skip: int) -> "Cursor[T]":
        check_none(self._cursor).skip(skip)
        return self

    def limit(self, limit: int) -> "Cursor[T]":
        check_none(self._cursor).limit(limit)
        return self

    def sort(self, *args: Any, **kwargs: Any) -> "Cursor[T]":
        check_none(self._cursor).sort(*args, **kwargs)
        return self

    def order(
            self,
            **kwargs: int
            ) -> "Cursor[T]":
        if len(kwargs) != 1:
            raise ValueError("order() requires one field = ASC or DESC.")
        for key, value in kwargs.items():
            if value not in (ASC, DESC):
                raise TypeError("Order value must be mogo.ASC or mogo.DESC.")
            self._order_entries.append((key, value))
            # According to the docs, only the LAST .sort() matters to
            # pymongo, so this SHOULD be safe
            check_none(self._cursor).sort(self._order_entries)
        return self

    def update(self, modifier: Dict[str, Any]) -> "Cursor[T]":
        if self._query is None:
            raise ValueError(
                "Cannot update on a cursor without a query. If you "
                "actually want to modify all values on a model, pass "
                "in an explicit {} to find().")
        check_none(self._model_class).update(
            self._query, modifier, multi=True)
        return self

    def change(self, **kwargs: Any) -> "Cursor[T]":
        modifier = {"$set": kwargs}
        return self.update(modifier)

    def distinct(self, key: str) -> Iterator[Any]:
        return cast(Iterator[Any], check_none(self._cursor).distinct(key))


if TYPE_CHECKING:
    from mogo.model import Model  # noqa: F401


__all__ = ["Cursor", "ASC", "DESC"]
