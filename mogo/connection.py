""" The wrapper for pymongo's connection stuff. """

from pymongo import Connection as PyConnection
from pymongo.errors import ConnectionFailure

class Connection(object):
    """
    This just caches a pymongo connection and adds
    a few shortcuts.
    """

    _instance = None
    connection = None
    _host = None
    _port = None
    _database = None

    @classmethod
    def instance(cls):
        """ Retrieves the shared connection. """
        if not cls._instance:
            cls._instance = Connection()
        return cls._instance

    @classmethod
    def connect(cls, database, *args, **kwargs):
        """
        Wraps a pymongo connection.
        TODO: Allow some of the URI stuff.
        """
        conn = cls.instance()
        conn._database = database
        conn.connection = PyConnection(*args, **kwargs)
        return conn.connection

    def get_database(self, database=None):
        """ Retrieves a database from an existing connection. """
        if not self.connection:
            raise ConnectionFailure('No connection')
        if not database:
            if not self._database:
                raise Exception('No database submitted')
            database = self._database
        return self.connection[database]

    def get_collection(self, collection, database=None):
        """ Retrieve a collection from an existing connection. """
        return self.get_database(database=database)[collection]

class Session(object):
    """ This class just wraps a connection instance """

    def __init__(self, database, *args, **kwargs):
        """ Stores a connection instance """
        self.connection = None
        self.database = database
        self.args = args
        self.kwargs = kwargs

    def connect(self):
        """ Connect to MongoDB """
        connection = Connection()
        connection._database = self.database
        connection.connection = PyConnection(*self.args, **self.kwargs)
        self.connection = connection

    def disconnect(self):
        """ Just a wrapper for the PyConnection disconnect. """
        self.connection.connection.disconnect()

    def __enter__(self):
        """ Open the connection """
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        """ Close the connection """
        self.disconnect()

def connect(database, *args, **kwargs):
    """
    Initializes a connection and the database. It returns
    the pymongo connection object so that end_request, etc.
    can be called if necessary.
    """
    return Connection.connect(database, *args, **kwargs)

def session(database, *args, **kwargs):
    """
    Returns a session object to be used with the `with` statement.
    """
    return Session(database, *args, **kwargs)
