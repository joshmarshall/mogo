""" 
This is really the core of the library. It's just a dict subclass
with a few wrapper methods. The idea is that you can access everything
like normal in pymongo if you wanted to, with keys aplenty, or you can
access values with attribute-style syntax.

Most importantly however, you can add methods to the model which is
sort of the main point of the MVC pattern of keeping logic with
the appropriate construct.

You don't need to specify fields or anything -- usage is pretty
simple:

class Foo(Model):
    # Silly custom method example.
    def custom_method(self):
        return self.get('bar', 'DEFAULT').lower()

"""

from mogo.connection import Connection
from mogo.cursor import Cursor

class Model(dict):
    """ 
    Subclass this class to create your documents. Basic usage
    is really simple:
    
    class Foo(Model):
        pass
        
    foo = Foo(user='admin', password='cheese')
    foo.save()
    for result in Foo.find({'user':'admin'}):
        print result.password
    """
    
    _id_field = '_id'
    _name = None
    _collection = None
    
    def __getattr__(self, name):
        """ Anything not specified in the class pulls from the dict """
        return self.get(name)
        # Would do something like this:
        # if not self.has_key(name):
        #     return getattr(self._get_collection(), name)
        # return self.get(name)
        # but I'm not sure of all the implications yet.
        
    def __setattr__(self, name, value):
        """ Sets a value to the dict if it's not an attribute. """
        if name in dir(self):
            return dict.__setattr__(self, name, value)
        return dict.__setitem__(self, name, value)
        
    def _get_id(self):
        """ 
        This is the internal id retrieval. 
        The .id property is the public method for getting
        an id, but we use this so the user can overwrite
        'id' if desired.
        """
        return self.get(self._id_field)
        
    def save(self, *args, **kwargs):
        """ 
        Just a wrapper for the pymongo collection .save().
        Allows all the same arguments. 
        """
        coll = self._get_collection()
        object_id = coll.save(self.copy(), *args, **kwargs)
        self[self._id_field] = object_id
        return object_id
        
    def remove(self, *args, **kwargs):
        """ 
        Uses the id in the collection.remove method. 
        Allows all the same arguments.
        """
        if not self._get_id():
            raise ValueError('No id has been set, so removal is impossible.')
        coll = self._get_collection()
        return coll.remove({self._id_field: self._get_id()}, *args, **kwargs)
        
    # This is designed so that the end user can still use 'id' as a Field 
    # if desired. All internal use should use model._get_id()
    @property
    def id(self):
        """ Returns the id. """
        return self._get_id()
    
    @classmethod
    def find_one(cls, *args, **kwargs):
        """ 
        Just a wrapper for collection.find_one(). Uses all
        the same arguments.
        """
        coll = cls._get_collection()
        result = coll.find_one(*args, **kwargs)
        if result:
            result = cls(**result)
        return result
        
    @classmethod
    def find(cls, *args, **kwargs):
        """ A wrapper for the pymongo cursor. Uses all the same arguments. """
        return Cursor(cls, *args, **kwargs)
    
    @classmethod
    def grab(cls, object_id):
        """ A shortcut to retrieve one object by its id. """
        return cls.find_one({cls._id_field: object_id})
    
    @classmethod    
    def _get_collection(cls):
        """ Connects and caches the collection connection object. """
        if not cls._collection:
            conn = Connection.instance()
            coll = conn.get_collection(cls._get_name())
            cls._collection = coll
        return cls._collection

    @classmethod
    def _get_name(cls):
        """ 
        Retrieves the collection name. 
        Overwrite _name to set it manually.
        """
        if cls._name:
            return cls._name
        return cls.__name__.lower()
        
    def __eq__(self, other):
        """
        This method compares two objects names and id values. 
        If they match, they are "equal".
        """
        this_id = self._get_id()
        other_id = other._get_id()
        if self.__class__.__name__ == other.__class__.__name__ and \
            this_id and other_id and \
            this_id == other_id:
            return True
        return False
        
    def __ne__(self, other):
        """ Returns the inverse of __eq__ ."""
        return not self.__eq__(self, other)
        
    # Friendly wrappers around collection
    @classmethod
    def count(cls):
        """ Just a wrapper for the collection.count() method. """
        return cls.find().count()