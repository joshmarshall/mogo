from typing import Any, Dict, Optional, TypeVar
from typing_extensions import TypeAlias

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.database import Database


T = TypeVar("T")
MDict: TypeAlias = Dict[str, Any]
MClient: TypeAlias = MongoClient[MDict]
MDatabase: TypeAlias = Database[MDict]
MCollection: TypeAlias = Collection[MDict]
MCursor: TypeAlias = Cursor[MDict]


def check_none(value: Optional[T]) -> T:
    if value is None:
        raise ValueError("Value is unexpectedly None.")
    return value
