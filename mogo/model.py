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
    created_at = Field(datetime, datetime.now)

    # Custom method example
    def set_password(self, password):
        self.password = hashlib.md5(password).hexdigest()
        self.save()

"""

from mogo.connection import Connection
from mogo.cursor import Cursor
from mogo.field import Field, EmptyRequiredField
from pymongo.dbref import DBRef
from pymongo.objectid import ObjectId
from mogo.decorators import notinstancemethod

class UseModelNewMethod(Exception):
    """ Raised when __init__ on a model is used incorrectly. """
    pass

class BiContextual(object):
    """ Probably a terrible, terrible idea. """

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, type=None):
        """ Return a properly named method. """
        if obj is None:
            return getattr(type, "_class_"+self.name)
        return getattr(obj, "_instance_"+self.name)

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
    _init_okay = False
    _fields = None

    @classmethod
    def new(cls, **kwargs):
        """ Overwrite in each model for custom instantiaion logic """
        cls._update_fields()
        cls._init_okay = True
        instance = cls()
        cls._init_okay = False
        for key, value in kwargs.iteritems():
            setattr(instance, key, value)
        instance._updated = []
        return instance

    @classmethod
    def _update_fields(cls):
        """ Initializes the fields from class attributes """
        if cls._fields is None:
            cls._fields = {}
            for attr_key, attr in cls.__dict__.iteritems():
                if attr_key.startswith('_'):
                    continue
                if not isinstance(attr, Field):
                    continue
                cls._fields[id(attr)] = attr_key
        return cls._fields

    def __init__(self, **kwargs):
        """ Just initializes the fields. This should ONLY be called
        from .new() or the Cursor.
        """
        self._updated = []
        if not self.__class__._init_okay and not kwargs.has_key("_id"):
            raise UseModelNewMethod("You must use Model.new to create a "+
                                    "new model instance.")
        super(Model, self).__init__(**kwargs)
        if self._fields is None: # hack, this should do it on its own
            self.__class__._update_fields()
        for field_name in self._fields.values():
            attr = self.__class__.__dict__[field_name]
            if not isinstance(attr, Field):
                continue
            self._fields[id(attr)] = field_name

            # set the default
            if attr.default is not None and not self.has_key(field_name):
                self[field_name] = attr._get_default()
        # Resetting dirty fields (new or coming from db)
        self._updated = []

    def _update_field_value(self, field, value):
        """ Sets the value of a field and enters it in _updated """
        if field not in self._updated:
            self._updated.append(field)
        self[field] = value

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
        """ Passthru to PyMongo's save after checking values """
        coll = self._get_collection()
        self._check_required()
        new_object_id = coll.save(self.copy(), *args, **kwargs)
        if not self._get_id():
            super(Model, self).__setitem__(self._id_field, new_object_id)
        return new_object_id

    @classmethod
    def _class_update(cls, *args, **kwargs):
        """ Direct passthru to PyMongo's update. """
        cls._update_fields()
        coll = cls._get_collection()
        # Maybe should do something 'clever' with the query?
        # E.g. transform Model instances to DBRefs automatically?
        return coll.update(*args, **kwargs)

    def _instance_update(self, **kwargs):
        """ Wraps keyword arguments with setattr and then uses PyMongo's
        update call.
         """
        object_id = self._get_id()
        spec = {self._id_field: object_id}
        # Currently the only argument we "pass on" is "safe"
        pass_kwargs = {}
        if "safe" in kwargs:
            pass_kwargs["safe"] = kwargs["safe"]
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        body = self._get_updated()
        self._check_required(*body.keys())
        coll = self._get_collection()
        return coll.update(spec, { "$set":  body }, **pass_kwargs)

    update = BiContextual("update")

    def _check_required(self, *field_names):
        """ Ensures that all required fields are set. """
        if not field_names:
            field_names = self._fields.values()
        for field_name in field_names:
            # check that required attributes have been set before,
            # or are currently being set
            if not self.has_key(field_name):
                field = self.__class__.__dict__[field_name]
                if field.required:
                    raise EmptyRequiredField("'%s' is required but empty"
                                             % field_name)

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
        cls._update_fields()
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
        cls._update_fields()
        return Cursor(cls, *args, **kwargs)

    @classmethod
    def group(cls, *args, **kwargs):
        """
        A quick wrapper for the pymongo collection map / reduce grouping.
        Will do more with this later.
        """
        cls._update_fields()
        return cls._get_collection().group(*args, **kwargs)

    @classmethod
    def search(cls, **kwargs):
        """
        Helper method that wraps keywords to dict and automatically
        turns instances into DBRefs.
        """
        cls._update_fields()
        query = {}
        for key, value in kwargs.iteritems():
            if isinstance(value, Model):
                value = value.get_ref()
            query[key] = value
        return cls.find(query)

    @classmethod
    def grab(cls, object_id):
        """ A shortcut to retrieve one object by its id. """
        cls._update_fields()
        if type(object_id) != cls._id_type:
            object_id = cls._id_type(object_id)
        return cls.find_one({cls._id_field: object_id})

    @classmethod
    def create_index(cls, *args, **kwargs):
        """ Wrapper for collection create_index() """
        cls._update_fields()
        return cls._get_collection().create_index(*args, **kwargs)

    @classmethod
    def ensure_index(cls, *args, **kwargs):
        """ Wrapper for collection ensure_index() """
        cls._update_fields()
        return cls._get_collection().ensure_index(*args, **kwargs)

    @classmethod
    def drop_indexes(cls, *args, **kwargs):
        """ Wrapper for collection drop_indexes() """
        cls._update_fields()
        return cls._get_collection().drop_indexes(*args, **kwargs)

    @classmethod
    def distinct(cls, key):
        """ Wrapper for collection distinct() """
        cls._update_fields()
        return cls.find().distinct(key)

    # Map Reduce and Group methods eventually go here.

    @classmethod
    def _get_collection(cls):
        """ Connects and caches the collection connection object. """
        cls._update_fields()
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
        cls._update_fields()
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
        cls._update_fields()
        return cls.find().count()

    @notinstancemethod
    def make_ref(cls, idval):
        """ Generates a DBRef for a given id. """
        if type(idval) != cls._id_type:
            # Casting to ObjectId (or str, or whatever is configured)
            idval = cls._id_type(idval)
        return DBRef(cls._get_name(), idval)

    def get_ref(self):
        """ Returns a DBRef for an document. """
        return DBRef(self._get_name(), self._get_id())

    def __repr__(self):
        return "<MogoModel:%s id:%s>" % (self._get_name(), self._get_id())
