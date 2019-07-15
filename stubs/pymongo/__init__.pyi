from pymongo.database import Database
from typing import Any


class MongoClient(object):

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 27017,
        document_class: type = dict,
        tz_aware: bool = False,
        connect: bool = True,
        **kwargs: Any) -> None: ...

    def drop_database(self, db: str, *args: Any, **kwargs: Any) -> None: ...

    def __getitem__(self, key: str) -> Database: ...

    def close(self) -> None: ...


ASCENDING: int = ...
DESCENDING: int = ...
