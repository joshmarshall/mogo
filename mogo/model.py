"""
This is really the core of the library. It's just a dict subclass
with a few wrapper methods. The idea is that you can access everything
like normal in pymongo if you wanted to, with keys aplenty, or you can
access values with attribute-style syntax.

Most importantly however, you can add methods to the model which is
sort of the main point of the MVC pattern of keeping logic with
the appropriate construct.

Specifying fields is optional, although it is recommended for
external references.

Usage example:

from mogo import Model
import hashlib
from datetime import datetime

class UserAccount(Model):

    name = Field(str)
    email = Field(str)
    company = ReferenceField(Company)
    created_at = Field(datetime, lambda: datetime.now())

    # Custom method example
    def set_password(self, password):
        self.password = hashlib.md5(password).hexdigest()
        self.save()

"""

from mogo.connection import Connection
from mogo.cursor import Cursor
from mogo.field import Field, ReferenceField
from pymongo.dbref import DBRef
from pymongo.objectid import ObjectId
from mogo.decorators import notinstancemethod
import inspect

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
    _id_type = ObjectId
    _name = None
    _collection = None
    _fields = None
    _updated = None

    def __init__(self, *args, **kwargs):
        """ Just initializes the fields... """
        self._fields = []
        self._updated = []
        dict.__init__(self, *args, **kwargs)
        for attr_key in dir(self.__class__):
            if attr_key.startswith('_'):
                continue
            attr = getattr(self.__class__, attr_key)
            if not isinstance(attr, Field):
                continue
            self._fields.append(attr_key)

            # set the default
            if hasattr(attr.default, '__call__'):
                # default is a callable
                value = attr.default()
            else:
                value = attr.default

            if attr_key in kwargs.keys():
                value = kwargs.get(attr_key)
            dict.__setattr__(self, attr_key, value)

    def __getattribute__(self, name):
        value = dict.__getattribute__(self, name)
        if type(value) is DBRef:
            model = None
            if self._fields and name in self._fields:
                field = getattr(self.__class__, name)
                if isinstance(field, ReferenceField):
                    model = field.model
            if not model:
                if value.collection == self._get_name():
                    model = self.__class__
                else:
                    # Making a "fake" model
                    class NewModel(Model):
                        _name = value.collection
                    model = NewModel
            # Lazy-loading now
            find_spec = {model._id_field: value.id}
            value = model.find_one(find_spec)
            # "Caching"
            dict.__setattr__(self, name, value)
        return value

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
        if name not in dir(self) or (
            self._fields and name in self._fields
        ):
            self._updated.append(name)
            self.__setitem__(name, value)
            if self._fields and name in self._fields:
                dict.__setattr__(self, name, value)
        else:
            return dict.__setattr__(self, name, value)

    def __setitem__(self, name, value):
        orig_value = getattr(self, name)
        if orig_value != value:
            self._updated.append(name)
        dict.__setitem__(self, name, value)
        if self._fields and name in self._fields:
            dict.__setattr__(self, name, value)

    def _get_id(self):
        """
        This is the internal id retrieval.
        The .id property is the public method for getting
        an id, but we use this so the user can overwrite
        'id' if desired.
        """
        return self.get(self._id_field)

    def _get_updated(self):
        """ Return recently updated contents of the model. """
        body = {}
        object_id = self.get(self._id_field)
        if object_id and not self._updated:
            return body
        #body[self._id_field] = self.get(self._id_field)
        if object_id:
            for key in self._updated:
                body[key] = self.get(key)
        else:
            body = self.copy()
        for key, value in body.iteritems():
            if isinstance(value, Model):
                """ Save the ref! """
                body[key] = DBRef(value._get_name(), value._get_id())
        return body

    def save(self, *args, **kwargs):
        """
        Determines whether to save or update, and does so.
        """
        coll = self._get_collection()
        body = {}
        object_id = self._get_id()
        body = self._get_updated()
        if body == None:
            return object_id
        if not object_id:
            object_id = coll.save(body, *args, **kwargs)
        else:
            spec = {self._id_field: object_id}
            coll.update(spec, {"$set": body}, *args, **kwargs)
        self._updated = []
        dict.__setitem__(self, self._id_field, object_id)
        return object_id

    def delete(self, *args, **kwargs):
        """
        Uses the id in the collection.remove method.
        Allows all the same arguments (except the spec/id).
        """
        if not self._get_id():
            raise ValueError('No id has been set, so removal is impossible.')
        coll = self._get_collection()
        return coll.remove(self._get_id(), *args, **kwargs)

    # Using notinstancemethod for classmethods which would
    # have dire, unintended consequences if used on an
    # instance. (Like, wiping a collection by trying to "remove"
    # a single document.)
    @notinstancemethod
    def remove(cls, *args, **kwargs):
        """ Just a wrapper around the collection's remove. """
        coll = cls._get_collection()
        return coll.remove(*args, **kwargs)

    @notinstancemethod
    def drop(cls, *args, **kwargs):
        """ Just a wrapper around the collection's drop. """
        coll = cls._get_collection()
        return coll.drop(*args, **kwargs)

    # This is designed so that the end user can still use 'id' as a Field
    # if desired. All internal use should use model._get_id()
    @property
    def id(self):
        """
        Returns the id. This is designed so that a subclass can still
        overwrite 'id' if desired... internal use should only use
        self._get_id(). May remove in the future if it's more annoying
        than helpful.
        """
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
        """
        A wrapper for the pymongo cursor. Uses all the
        same arguments.
        """
        return Cursor(cls, *args, **kwargs)

    @classmethod
    def group(cls, *args, **kwargs):
        """
        A quick wrapper for the pymongo collection map / reduce grouping.
        Will do more with this later.
        """
        return cls._get_collection().group(*args, **kwargs)

    @classmethod
    def search(cls, **kwargs):
        """
        Helper method that wraps keywords to dict and automatically
        turns instances into DBRefs.
        """
        query = {}
        for key, value in kwargs.iteritems():
            if isinstance(value, Model):
                value = value.get_ref()
            query[key] = value
        return cls.find(query)

    @classmethod
    def grab(cls, object_id):
        """ A shortcut to retrieve one object by its id. """
        if type(object_id) != cls._id_type:
            object_id = cls._id_type(object_id)
        return cls.find_one({cls._id_field: object_id})

    @classmethod
    def create_index(cls, *args, **kwargs):
        """ Wrapper for collection create_index() """
        return cls._get_collection().create_index(*args, **kwargs)

    @classmethod
    def ensure_index(cls, *args, **kwargs):
        """ Wrapper for collection ensure_index() """
        return cls._get_collection().ensure_index(*args, **kwargs)

    @classmethod
    def drop_indexes(cls, *args, **kwargs):
        """ Wrapper for collection drop_indexes() """
        return cls._get_collection().drop_indexes(*args, **kwargs)

    @classmethod
    def distinct(cls, key):
        """ Wrapper for collection distinct() """
        return self.find().distinct(key)

    # Map Reduce and Group methods eventually go here.

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
        if not isinstance(other, Model):
            return False
        this_id = self._get_id()
        other_id = other._get_id()
        if self.__class__.__name__ == other.__class__.__name__ and \
            this_id and other_id and \
            this_id == other_id:
            return True
        return False

    def __ne__(self, other):
        """ Returns the inverse of __eq__ ."""
        return not self.__eq__(other)

    # Friendly wrappers around collection
    @classmethod
    def count(cls):
        """ Just a wrapper for the collection.count() method. """
        return cls.find().count()

    @notinstancemethod
    def make_ref(cls, idval):
        """ Generates a DBRef for a given id. """
        if type(idval) != self._id_type:
            # Casting to ObjectId (or str, or whatever is configured)
            idval = self._id_type(id_val)
        return DBRef(self._get_name(), idval)

    def get_ref(self):
        """ Returns a DBRef for an document. """
        return DBRef(self._get_name(), self._get_id())

    def __repr__(self):
        return "<MogoModel:%s id:%s>" % (self._get_name(), self._get_id())
