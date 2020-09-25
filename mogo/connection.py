""" The wrapper for pymongo's connection stuff. """

from urllib.parse import urlparse
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from types import TracebackType
from typing import Any, Optional, Type


class Connection(object):
    """
    This just caches a pymongo connection and adds
    a few shortcuts.
    """

    _instance = None  # type: Optional['Connection']
    _database = None  # type: Optional[str]
    connection = None  # type: Optional[MongoClient]

    @classmethod
    def instance(cls) -> "Connection":
        """ Retrieves the shared connection. """
        if not cls._instance:
            cls._instance = Connection()
        return cls._instance

    @classmethod
    def connect(
            cls, database: Optional[str] = None,
            uri: str = "mongodb://localhost:27017",
            **kwargs: Any) -> MongoClient:
        """
        Wraps a pymongo connection.
        TODO: Allow some of the URI stuff.
        """
        if not database:
            database = urlparse(uri).path
            while database.startswith("/"):
                database = database[1:]
            if not database:
                raise ValueError("A database name is required to connect.")

        conn = cls.instance()
        conn._database = database
        conn.connection = MongoClient(uri, **kwargs)
        return conn.connection

    def get_database(self, database: Optional[str] = None) -> Database:
        """ Retrieves a database from an existing connection. """
        if not self.connection:
            raise ConnectionFailure('No connection')
        if not database:
            if not self._database:
                raise Exception('No database submitted')
            database = self._database
        return self.connection[database]

    def get_collection(
            self,
            collection: str,
            database: Optional[str] = None) -> Collection:
        """ Retrieve a collection from an existing connection. """
        return self.get_database(database=database)[collection]


class Session(object):
    """ This class just wraps a connection instance """

    connection = None  # type: Optional[Connection]
    database = None  # type: Optional[str]
    args = None  # type: Any
    kwargs = None  # type: Any

    def __init__(self, database: str, *args: Any, **kwargs: Any) -> None:
        """ Stores a connection instance """
        self.connection = None
        self.database = database
        self.args = args
        self.kwargs = kwargs

    def connect(self) -> None:
        """ Connect to MongoDB """
        connection = Connection()
        connection._database = self.database
        connection.connection = MongoClient(*self.args, **self.kwargs)
        self.connection = connection

    def disconnect(self) -> None:
        # PyMongo removed the disconnect keyword, close() is now used.
        self.close()

    def close(self) -> None:
        if self.connection is not None and \
                self.connection.connection is not None:
            self.connection.connection.close()

    def __enter__(self) -> 'Session':
        """ Open the connection """
        self.connect()
        return self

    def __exit__(
            self,
            exc_type: Optional[Type[Exception]],
            exc_value: Optional[Exception],
            traceback: Optional[TracebackType]) -> None:
        """ Close the connection """
        self.disconnect()


def connect(*args: Any, **kwargs: Any) -> MongoClient:
    """
    Initializes a connection and the database. It returns
    the pymongo connection object so that end_request, etc.
    can be called if necessary.
    """
    return Connection.connect(*args, **kwargs)


def session(database: str, *args: Any, **kwargs: Any) -> Session:
    """
    Returns a session object to be used with the `with` statement.
    """
    return Session(database, *args, **kwargs)


__all__ = ["connect", "session"]
