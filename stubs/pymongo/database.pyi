from pymongo.collection import Collection


class Database(object):

    def __getitem__(self, key: str) -> Collection: ...
