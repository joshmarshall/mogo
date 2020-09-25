from typing import Any


class DBRef(object):

    id = None  # type: Any

    def __init__(self, collection: str, idval: Any) -> None: ...
