from typing import Any, Optional, Sequence, TypeVar


class UpdateResult(object):
    upserted_id: Optional[Any]


class InsertOneResult(object):
    inserted_id: Any


class InsertManyResult(object):
    inserted_ids: Sequence[Any]


class DeleteResult(object):
    deleted_count: int
