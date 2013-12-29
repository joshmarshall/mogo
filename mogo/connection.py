""" The wrapper for pymongo's connection stuff. """

from pymongo import MongoClient
import urlparse

from mogo.exceptions import InvalidConnectionURI, DatabaseNameMismatch


_DEFAULT_URI = "mongodb://localhost:27017"


class Connection(object):

    def __init__(self, database_name, database_uri):
        parsed_database_uri = urlparse.urlparse(database_uri)
        if parsed_database_uri.scheme != "mongodb":
            raise InvalidConnectionURI(
                "Mogo requires a properly-formed mongodb:// connection URI.")

        uri_database_name = urlparse.urlparse(database_uri).path
        while uri_database_name.startswith("/"):
            uri_database_name = uri_database_name[1:]

        if uri_database_name and uri_database_name != database_name:
            raise DatabaseNameMismatch(
                "The database name provided via the connection URI (%s) "
                "does not match the explicit database name provided (%s) " % (
                    uri_database_name, database_name))

        self._client = MongoClient(database_uri)
        self._database_name = database_name

    def get_client(self):
        return self._client

    def get_database(self):
        """ Retrieves a database from an existing connection. """
        return self._client[self._database_name]

    def get_collection(self, collection):
        """ Retrieve a collection from an existing connection. """
        return self.get_database()[collection]

    def disconnect(self):
        self._client.disconnect()


class Session(object):
    """ This class just wraps a connection instance """

    def __init__(self, database_name, database_uri):
        """ Stores a connection instance """
        self._database_name = database_name
        self._database_uri = database_uri
        self._connection = Connection(self._database_name, self._database_uri)

    def get_connection(self):
        return self._connection

    def disconnect(self):
        return self._connection.disconnect()

    def __enter__(self):
        """ Open the connection """
        global _INSTANCE
        self._original_connection = _INSTANCE
        _INSTANCE = self._connection
        return self

    def __exit__(self, type, value, traceback):
        """ Close the connection """
        global _INSTANCE
        self.disconnect()
        _INSTANCE = self._original_connection


_INSTANCE = None
_DATABASE_NAME = None
_DATABASE_URI = None


def instance():
    return _INSTANCE


def connect(database_name, database_uri=_DEFAULT_URI):
    """
    Initializes a connection and the database. It returns
    the pymongo connection object so that end_request, etc.
    can be called if necessary.
    """
    global _INSTANCE, _DATABASE_NAME, _DATABASE_URI
    if _INSTANCE:
        if _DATABASE_NAME == database_name and _DATABASE_URI == database_uri:
            return _INSTANCE
        _INSTANCE.disconnect()
    _INSTANCE = Connection(database_name, database_uri)
    _DATABASE_NAME = database_name
    _DATABASE_URI = database_uri
    return _INSTANCE


def session(database_name, database_uri=_DEFAULT_URI):
    """
    Returns a session object to be used with the `with` statement.
    """
    return Session(database_name, database_uri)
