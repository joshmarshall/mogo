from pymongo.client_session import ClientSession
from pymongo.collation import Collation
from pymongo.command_cursor import CommandCursor
from pymongo.results import DeleteResult, UpdateResult, InsertOneResult

from typing import Any, Dict, Iterator, Optional, Sequence, Tuple, TypeVar, Union


class Collection(object):

    def update_one(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
        bypass_document_validation: bool = False,
        collation: Optional[Collation] = None,
        array_filters: Optional[Dict[str, Any]] = None,
        session: Optional[ClientSession] = None) -> UpdateResult: ...

    def update_many(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
        array_filters: Optional[Dict[str, Any]] = None,
        bypass_document_validation: bool = False,
        collation: Optional[Collation] = None,
        session: Optional[ClientSession] = None) -> UpdateResult: ...

    def replace_one(
        self,
        filter: Dict[str, Any],
        replacement: Dict[str, Any],
        upsert: bool = False,
        bypass_document_validation: bool = False,
        collation: Optional[Collation] = None,
        array_filters: Optional[Dict[str, Any]] = None,
        session: Optional[ClientSession] = None) -> UpdateResult: ...

    def insert_one(self,
        document: Dict[str, Any],
        bypass_document_validation: bool = False,
        session: Optional[ClientSession] = None) -> InsertOneResult: ...

    def delete_one(
        self,
        filter: Dict[str, Any],
        collation: Optional[Collation] = None,
        session: Optional[ClientSession] = None) -> DeleteResult: ...

    def delete_many(
        self,
        filter: Dict[str, Any],
        collation: Optional[Collation] = None,
        session: Optional[ClientSession] = None) -> DeleteResult: ...

    def drop(self, session: Optional[ClientSession] = None) -> None: ...

    def find_one(
        self,
        filter: Optional[Union[Dict[str, Any], Any]] = None,
        *args: Any,
        **kwargs: Any) -> Optional[Dict[str, Any]]: ...

    def find(
        self,
        filter: Optional[Dict[str, Any]] = None,
        projection: Optional[Sequence[str]] = None,
        skip: int = 0,
        limit: int = 0,
        no_cursor_timeout: bool = False,
        sort: Optional[Sequence[Tuple[str, int]]] = None,
        allow_partial_results: bool = False,
        oplog_replay: bool = False,
        batch_size: int = 0,
        collation: Optional[Collation] = None,
        hint: Optional[Sequence[Tuple[str, int]]] = None,
        max_time_ms: Optional[int] = None,
        max: Optional[Sequence[Tuple[str, int]]] = None,
        min: Optional[Sequence[Tuple[str, int]]] = None,
        return_key: bool = False,
        show_record_id: bool = False,
        snapshot: bool = False,
        comment: Optional[str] = None,
        session: Optional[ClientSession] = None) -> Iterator[Dict[str, Any]]: ...

    def group(
        self,
        key: Dict[str, Any],
        condition: Dict[str, Any],
        initial: Any,
        reduce: str,
        finalize: Optional[str] = None,
        **kwargs: Any) -> Iterator[Dict[str, Any]]: ...

    def create_index(
        self,
        keys: Sequence[Tuple[str, int]],
        session: Optional[ClientSession] = None,
        **kwargs: Any) -> None: ...

    def drop_index(
        self,
        index_or_name: Union[str, Sequence[Tuple[str, int]]],
        session: Optional[ClientSession] = None,
        **kwargs: Any) -> None: ...

    def drop_indexes(
        self,
        session: Optional[ClientSession] = None,
        **kwargs: Any) -> None: ...

    def ensure_index(
        self,
        key_or_list: Union[str, Sequence[Tuple[str, int]]],
        cache_for: int = 300,
        **kwargs: Any) -> None: ...

    def count_documents(
        self,
        filter: Dict[str, Any],
        session: Optional[ClientSession] = None,
        **kwargs: Any) -> int: ...

    def aggregate(
        self,
        pipeline: Sequence[Dict[str, Any]],
        session: Optional[ClientSession] = None,
        **kwargs: Any) -> Iterator[Dict[str, Any]]: ...
