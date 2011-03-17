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
        
def connect(database, *args, **kwargs):
    """ 
    Initializes a connection and the database. It returns
    the pymongo connection object so that end_request, etc.
    can be called if necessary.
    """
    return Connection.connect(database, *args, **kwargs)
