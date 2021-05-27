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

import inspect
import logging
import warnings

import mogo
from mogo.connection import Connection, Session
from mogo.decorators import notinstancemethod
from mogo.cursor import Cursor
from mogo.field import Field, EmptyRequiredField
from mogo.helpers import check_none

from bson.dbref import DBRef
from bson.objectid import ObjectId
from pymongo.collection import Collection
from pymongo.results import DeleteResult, UpdateResult

import typing
from typing import Any, Callable, cast, Dict, Iterator
from typing import Optional, Sequence, Tuple, Type, TypeVar, Union


M = TypeVar("M", bound="Model")
P = TypeVar("P", bound="PolyModel")


_UpdateCallable = Callable[..., UpdateResult]


class BiContextualUpdate(object):

    def __get__(
            self,
            obj: Optional[M],
            otype: Optional[Type[M]] = None) -> _UpdateCallable:
        """ Return a properly named method. """
        if obj is None:
            if otype is not None:
                return otype._class_update
            else:
                raise Exception("Neither model nor instance provided.")
        else:
            return obj._instance_update


class InvalidUpdateCall(Exception):
    """ Raised whenever update is called on a new model """
    pass


class UnknownField(Exception):
    """ Raised whenever an invalid field is accessed and the
    AUTO_CREATE_FIELDS is False.
    """
    pass


class NewModelClass(type):
    """ Metaclass for inheriting field lists """

    def __new__(  # type: ignore
            cls,
            name: str,
            bases: Tuple[type, ...],
            attributes: Dict[str, Any]) -> Type[M]:
        # Emptying fields by default
        attributes["__fields"] = {}
        new_model = cast(
            Type[M],
            super().__new__(cls, name, bases, attributes))  # type: Type[M]
        # pre-populate fields
        new_model._update_fields()
        if hasattr(new_model, "_child_models"):
            new_model._child_models = {}
        return new_model

    def __setattr__(cls, name: str, value: Any) -> None:
        """ Catching new field additions to classes """
        super().__setattr__(name, value)
        if isinstance(value, Field):
            # Update the fields, because they have changed
            cast(Type[Model], cls)._update_fields()


class Model(metaclass=NewModelClass):
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

    _id_field = "_id"  # type: str
    _id_type = ObjectId  # type: Any
    _name = None  # type: Optional[str]
    _pymongo_data = None  # type: Optional[Dict[str, Any]]
    _collection = None  # type: Optional[Collection]
    _child_models = None  # type: Optional[Dict[Any, Type["PolyModel"]]]
    _init_okay = False  # type: bool
    __fields = None  # type: Optional[Dict[int, str]]

    AUTO_CREATE_FIELDS = None  # type: Optional[bool]

    # DEPRECATED
    @classmethod
    def new(cls: Type[M], **kwargs: Any) -> M:
        """ Overwrite in each model for custom instantiaion logic """
        instance = cls(**kwargs)  # type: M
        return instance

    # Dict-compatibility methods

    def get(self: M, key: str, default: Optional[Any] = None) -> Optional[Any]:
        return check_none(self._pymongo_data).get(key, default)

    def copy(self: M) -> Dict[str, Any]:
        return check_none(self._pymongo_data).copy()

    def __setitem__(self: M, key: str, value: Any) -> None:
        check_none(self._pymongo_data).__setitem__(key, value)

    def __getitem__(self: M, key: str) -> Any:
        return check_none(self._pymongo_data).__getitem__(key)

    def __delitem__(self: M, key: str) -> Any:
        return check_none(self._pymongo_data).__delitem__(key)

    def __contains__(self: M, item: str) -> bool:
        return check_none(self._pymongo_data).__contains__(item)

    def __hash__(self: M) -> Any:
        hash_impl = check_none(self._pymongo_data).__hash__
        if hash_impl is None:
            return None
        return hash_impl()

    def __len__(self: M) -> int:
        return check_none(self._pymongo_data).__len__()

    def __iter__(self: M) -> Iterator[str]:
        return check_none(self._pymongo_data).__iter__()

    # Model methods

    @classmethod
    def use(cls: Type[M], session: Session) -> Type[M]:
        """ Wraps the class to use a specific connection session """
        # have to ignore type here because mypy isn't able to follow the
        # dynamic base presented by `cls` (e.g. Type[M])
        class Wrapped(cls):  # type: ignore
            pass

        Wrapped.__name__ = cls.__name__
        connection = session.connection
        if connection is None:
            raise Exception("No connection for session.")
        collection = connection.get_collection(
            Wrapped._get_name())  # type: Collection
        Wrapped._collection = collection
        return Wrapped

    @classmethod
    def create(cls: Type[M], **kwargs: Any) -> M:
        """ Create a new model and save it. """
        if hasattr(cls, "new"):
            model = cls.new(**kwargs)  # type: M
        else:
            model = cls(**kwargs)
        model.save()
        return model

    def __init__(self: M, **kwargs: Any) -> None:
        """ Creates an instance of the model, without saving it. """
        super().__init__()
        self._pymongo_data = {}
        # compute once
        create_fields = self._auto_create_fields
        is_new_instance = self._id_field not in kwargs
        for field, value in kwargs.items():
            if is_new_instance:
                if field in self._fields.values():
                    # Running validation, if the field exists
                    setattr(self, field, value)
                else:
                    if not create_fields:
                        raise UnknownField("Unknown field {}".format(field))
                    self.add_field(field, Field())
                    setattr(self, field, value)
            else:
                self[field] = value

        for field_name in self._fields.values():
            attr = getattr(self.__class__, field_name)
            self._fields[attr.id] = field_name

            # set the default
            attr._set_default(self, field_name)

    @classmethod
    def _get_fields(cls: Type[M]) -> Dict[int, str]:
        return check_none(cls.__fields)

    @property
    def _auto_create_fields(self: M) -> bool:
        if self.AUTO_CREATE_FIELDS is not None:
            return self.AUTO_CREATE_FIELDS
        return mogo.AUTO_CREATE_FIELDS

    @property
    def _fields(self: M) -> Dict[int, str]:
        return self._get_fields()

    @classmethod
    def _update_fields(cls: Type[M]) -> None:
        """ (Re)update the list of fields """
        cls.__fields = {}
        for attr_key in dir(cls):
            attr = getattr(cls, attr_key)
            if not isinstance(attr, Field):
                continue
            cls.__fields[attr.id] = attr_key

    @classmethod
    def add_field(
            cls: Type[M],
            field_name: str,
            new_field_descriptor: Any) -> None:
        """ Adds a new field to the class """
        assert(isinstance(new_field_descriptor, Field))
        setattr(cls, field_name, new_field_descriptor)
        cls._update_fields()

    def _get_id(self: M) -> Optional[Any]:
        """
        This is the internal id retrieval.
        The .id property is the public method for getting
        an id, but we use this so the user can overwrite
        'id' if desired.
        """
        return self.get(self._id_field)

    def save(self: M, *args: Any, **kwargs: Any) -> Any:
        """ Passthru to PyMongo's save after checking values """
        coll = self._get_collection()
        self._check_required()
        if "safe" in kwargs:
            warn_about_keyword_deprecation("safe")
            del kwargs["safe"]
        object_id = self._get_id()
        if object_id is None:
            result = coll.insert_one(self.copy())
            object_id = result.inserted_id
            self.__setitem__(self._id_field, object_id)
        else:
            spec = {self._id_field: object_id}
            coll.replace_one(spec, self.copy(), upsert=True)
        return object_id

    @classmethod
    def _class_update(
            cls: Type[M], *args: Any, **kwargs: Any) -> UpdateResult:
        """ Direct passthru to PyMongo's update. """
        if "safe" in kwargs:
            warn_about_keyword_deprecation("safe")
            del kwargs["safe"]
        coll = cls._get_collection()  # type: Collection
        if "multi" in kwargs and kwargs.pop("multi") is True:
            return coll.update_many(*args, **kwargs)
        return coll.update_one(*args, **kwargs)

    def _instance_update(self: M, **kwargs: Any) -> UpdateResult:
        """ Wraps keyword arguments with setattr and then uses PyMongo's
        update call.
         """
        object_id = self._get_id()
        if not object_id:
            raise InvalidUpdateCall("Cannot call update on an unsaved model")
        spec = {self._id_field: object_id}
        if "safe" in kwargs:
            del kwargs["safe"]
            warn_about_keyword_deprecation("safe")
        body = {}
        checks = []
        for key, value in kwargs.items():
            if key in self._fields.values():
                setattr(self, key, value)
            else:
                logging.warning("No field for {}".format(key))
                self[key] = value
            # Attribute names to check.
            checks.append(key)
            # Field names in collection.
            field = getattr(self.__class__, key)
            field_name = field._get_field_name(self)
            # setting the body key to the pymongo value
            body[field_name] = self[field_name]
        self._check_required(*checks)
        coll = self._get_collection()
        return coll.update_one(spec, {"$set": body})

    update = BiContextualUpdate()

    def _check_required(self: M, *field_args: str) -> None:
        """ Ensures that all required fields are set. """
        field_names = list(field_args)  # type: Sequence[str]
        if not field_names:
            field_names = list(self._fields.values())
        for field_name in field_names:
            # check that required attributes have been set before,
            # or are currently being set
            field = cast("Field[Any]", getattr(self.__class__, field_name))
            storage_name = field._get_field_name(self)
            if storage_name not in self:
                if field._is_required():
                    raise EmptyRequiredField(
                        "'{}' is required but empty".format(field_name))

    def delete(self: M, *args: Any, **kwargs: Any) -> DeleteResult:
        """
        Uses the id in the collection.remove method.
        Allows all the same arguments (except the spec/id).
        """
        if not self._get_id():
            raise ValueError('No id has been set, so removal is impossible.')
        coll = self._get_collection()
        return coll.delete_one(
            {self._id_field: self._get_id()}, *args, **kwargs)

    # Using notinstancemethod for classmethods which would
    # have dire, unintended consequences if used on an
    # instance. (Like, wiping a collection by trying to "remove"
    # a single document.)
    @notinstancemethod
    @classmethod
    def remove(cls: Type[M], *args: Any, **kwargs: Any) -> DeleteResult:
        """ Just a wrapper around the collection's remove. """
        if not args:
            # If you get this exception you are calling remove with no
            # arguments or with only keyword arguments, which is not
            # supported (and would remove all entries in the current
            # collection if it was.) If you really want to delete
            # everything in a collection, pass an empty dictionary like
            # Model.remove({})
            raise ValueError(
                'remove() requires a query when called with keyword arguments')
        coll = cls._get_collection()
        if "multi" in kwargs and kwargs.pop("multi") is True:
            return coll.delete_many(*args, **kwargs)
        else:
            return coll.delete_one(*args, **kwargs)

    @notinstancemethod
    @classmethod
    def drop(cls: Type[M], *args: Any, **kwargs: Any) -> Any:
        """ Just a wrapper around the collection's drop. """
        coll = cls._get_collection()
        return coll.drop(*args, **kwargs)

    # This is designed so that the end user can still use 'id' as a Field
    # if desired. All internal use should use model._get_id()
    @property
    def id(self: M) -> Optional[Any]:
        """
        Returns the id. This is designed so that a subclass can still
        overwrite 'id' if desired... internal use should only use
        self._get_id(). May remove in the future if it's more annoying
        than helpful.
        """
        return self._get_id()

    _id = id

    @classmethod
    def find_one(cls: Type[M], *args: Any, **kwargs: Any) -> Optional[M]:
        """
        Just a wrapper for collection.find_one(). Uses all
        the same arguments.
        """
        if kwargs and not args:
            # If you get this exception you should probably be calling first,
            # not find_one. If you really want find_one, pass an empty dict:
            # Model.find_one({}, timeout=False)
            raise ValueError(
                "find_one() requires a query when called with "
                "keyword arguments")
        if "timeout" in kwargs:
            warn_about_keyword_deprecation("timeout")
            del kwargs["timeout"]
        coll = cls._get_collection()  # type: Collection
        find_result = coll.find_one(
            *args, **kwargs)  # type: Optional[Dict[str, Any]]
        result = None  # type: Optional[M]
        if find_result is not None:
            result = cls(**find_result)
        return result

    @classmethod
    def find(cls: Type[M], *args: Any, **kwargs: Any) -> Cursor[M]:
        """
        A wrapper for the pymongo cursor. Uses all the
        same arguments.
        """
        if kwargs and not args:
            # If you get this exception you should probably be calling search,
            # not find. If you really want to call find, pass an empty dict:
            # Model.find({}, timeout=False)
            raise ValueError(
                'find() requires a query when called with keyword arguments')

        if "timeout" in kwargs:
            warn_about_keyword_deprecation("timeout")
            del kwargs["timeout"]

        return Cursor(cls, *args, **kwargs)

    @classmethod
    def group(
            cls: Type[M],
            *args: Any,
            **kwargs: Any) -> Iterator[Dict[str, Any]]:
        # This is deprecated, and will be removed from PyMongo in version 4.0
        return cls._get_collection().group(*args, **kwargs)

    @notinstancemethod
    @classmethod
    def aggregate(
            cls: Type[M],
            pipeline: Sequence[Dict[str, Any]],
            **kwargs: Any) -> Iterator[Dict[str, Any]]:
        return cls._get_collection().aggregate(pipeline, **kwargs)

    @classmethod
    def search(cls: Type[M], **kwargs: Any) -> Cursor[M]:
        """
        Helper method that wraps keywords to dict and automatically
        turns instances into DBRefs.
        """
        query = {}
        for key, value in kwargs.items():
            if isinstance(value, Model):
                value = value.get_ref()
            field = getattr(cls, key)

            # Try using custom field name in field.
            if field._get_field_name(cls) != key:
                key = field._get_field_name(cls)

            query[key] = value
        return cls.find(query)

    @classmethod
    def search_or_create(cls: Type[M], **kwargs: Any) -> M:
        "search for an instance that matches kwargs or make one with __init__"
        cursor = cls.search(**kwargs)  # type: Cursor[M]
        obj = cursor.first()  # type: Optional[M]
        if obj is not None:
            return obj
        return cls.create(**kwargs)

    @classmethod
    def first(cls: Type[M], **kwargs: Any) -> Optional[M]:
        """ Helper for returning Blah.search(foo=bar).first(). """
        result = cls.search(**kwargs)  # type: Cursor[M]
        return result.first()

    @classmethod
    def grab(cls: Type[M], object_id: Any) -> Optional[M]:
        """ A shortcut to retrieve one object by its id. """
        if type(object_id) != cls._id_type:
            object_id = cls._id_type(object_id)
        return cls.find_one({cls._id_field: object_id})

    @classmethod
    def create_index(cls: Type[M], *args: Any, **kwargs: Any) -> Any:
        """ Wrapper for collection create_index() """
        return cls._get_collection().create_index(*args, **kwargs)

    @classmethod
    def ensure_index(cls: Type[M], *args: Any, **kwargs: Any) -> Any:
        """ Wrapper for collection ensure_index() """
        return cls._get_collection().ensure_index(*args, **kwargs)

    @classmethod
    def drop_indexes(cls: Type[M], *args: Any, **kwargs: Any) -> Any:
        """ Wrapper for collection drop_indexes() """
        return cls._get_collection().drop_indexes(*args, **kwargs)

    @classmethod
    def distinct(cls: Type[M], key: str) -> Iterator[Any]:
        """ Wrapper for collection distinct() """
        return cls.find().distinct(key)

    # Map Reduce and Group methods eventually go here.

    @classmethod
    def _get_collection(cls: Type[M]) -> Collection:
        """ Connects and caches the collection connection object. """
        if not cls._collection:
            conn = Connection.instance()
            coll = conn.get_collection(cls._get_name())  # type: Collection
            cls._collection = coll
        return cls._collection

    @classmethod
    def _get_name(cls: Type[M]) -> str:
        """
        Retrieves the collection name.
        Overwrite _name to set it manually.
        """
        if cls._name:
            return cls._name
        return cls.__name__.lower()

    def __eq__(self: M, other: Any) -> bool:
        """
        This method compares two objects names and id values.
        If they match, they are "equal".
        """
        if other is None:
            return False

        if not isinstance(other, Model):
            return False

        this_id = self._get_id()
        other_id = other._get_id()
        if self._get_name() == other._get_name() and \
                this_id and other_id and this_id == other_id:
            return True
        return False

    def __ne__(self: M, other: Any) -> bool:
        """ Returns the inverse of __eq__ ."""
        return not self.__eq__(other)

    # Friendly wrappers around collection
    @classmethod
    def count(cls: Type[M]) -> int:
        return cls.find().count()

    @notinstancemethod
    @classmethod
    def count_documents(
            cls: Type[M],
            filter: Dict[str, Any],
            *args: Any,
            **kwargs: Any) -> int:
        return cls._get_collection().count_documents(filter, *args, **kwargs)

    @notinstancemethod
    @classmethod
    def make_ref(cls: Type[M], idval: Any) -> DBRef:
        """ Generates a DBRef for a given id. """
        if type(idval) != cls._id_type and callable(cls._id_type):
            # Casting to ObjectId (or str, or whatever is configured)
            id_type = cast(Callable[..., M], cls._id_type)
            idval = id_type(idval)
        return DBRef(cls._get_name(), idval)

    def get_ref(self: M) -> DBRef:
        """ Returns a DBRef for an document. """
        idval = self._get_id()
        if idval is not None:
            return DBRef(self._get_name(), idval)
        raise Exception("Missing object ID -- cannot retrieve DBRef.")

    def __unicode__(self: M) -> str:
        """ Returns string representation. Overwrite in custom models. """
        return "<MogoModel:{} id:{}>".format(self._get_name(), self._get_id())

    def __str__(self: M) -> str:
        return self.__unicode__()

    def __repr__(self: M) -> str:
        return self.__unicode__()


class PolyModel(Model):
    """ A base class for inherited models """

    _polyinfo = None  \
        # type: Optional[Dict[str, Union[str, Type["PolyModel"]]]]

    def __new__(cls: Type[P], **kwargs: Any) -> P:
        """ Creates a model of the appropriate type """
        # use the base model by default
        create_class = cls
        key_field = getattr(cls, cls.get_child_key(), None)
        key = kwargs.get(cls.get_child_key())
        if cls._child_models is not None:
            if not key and key_field:
                key = key_field._get_default()
            if key in cls._child_models:
                create_class = cast(Type[P], cls._child_models[key])
        return cast(P, super().__new__(create_class))

    @classmethod
    def get_child_key(cls: Type[P]) -> str:
        raise NotImplementedError("`get_child_key() -> str` not implemented.")

    # the following need double noqa: comments because Flake8 performs the
    # check at different levels depending on the version of Python...

    @typing.overload  # noqa: F811
    @classmethod
    def register(cls: Type[P], value: Type[P]) -> Type[P]: ...  # noqa: F811

    @typing.overload  # noqa: F811
    @classmethod
    def register(  # noqa: F811
        cls: Type[P], value: Optional[Any] = None,
        name: Optional[str] = None) -> Callable[[Type[P]], Type[P]]: ...

    @classmethod  # noqa: F811
    def register(  # noqa: F811
            cls: Type[P],
            value: Optional[Union[Any, Type[P]]] = None,
            name: Optional[str] = None) -> \
            Union[
                Type[P],
                Callable[[Type[P]], Type[P]]]:
        """ Decorator for registering a submodel """

        if value is None:
            def wrap(child_cls: Type[P]) -> Type[P]:
                poly_name = name or child_cls.__name__.lower()
                poly_value = poly_name
                return _wrap_polymodel(cls, poly_name, poly_value, child_cls)
            return wrap
        elif not inspect.isclass(value):
            def wrap(child_cls: Type[P]) -> Type[P]:
                poly_name = name or child_cls.__name__.lower()
                return _wrap_polymodel(cls, poly_name, value, child_cls)
            return wrap
        elif issubclass(value, cls):
            child_cls = cast(Type[P], value)
            name = child_cls.__name__.lower()
            value = name
            return _wrap_polymodel(cls, name, value, child_cls)
        else:
            raise ValueError(
                "Could not register polymodel value {}".format(value))

    @classmethod
    def _update_search_spec(
            cls: Type[P], spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """ Update the search specification on child polymodels. """
        spec = spec or {}
        if cls._polyinfo is not None:
            value = cls._polyinfo["value"]
            polyclass = cast(P, cls._polyinfo["parent"])
            spec.setdefault(polyclass.get_child_key(), value)
        return spec

    @classmethod
    def find(
            cls: Type[P],
            spec: Optional[Dict[str, Any]] = None,
            *args: Any,
            **kwargs: Any) -> Cursor[P]:
        """ Add key to search params """
        spec = cls._update_search_spec(spec)
        return super().find(spec, *args, **kwargs)

    @classmethod
    def find_one(
            cls: Type[P],
            spec: Optional[Dict[str, Any]] = None,
            *args: Any,
            **kwargs: Any) -> Optional[P]:
        """ Add key to search params for single result """
        spec = cls._update_search_spec(spec)
        return super().find_one(spec, *args, **kwargs)

    @notinstancemethod
    @classmethod
    def aggregate(
            cls: Type[P],
            pipeline: Sequence[Dict[str, Any]],
            **kwargs: Any) -> Iterator[Dict[str, Any]]:
        spec = cls._update_search_spec({})
        if spec:
            if len(pipeline) > 0 and "$match" in pipeline[0]:
                pipeline[0]["$match"].update(spec)
            else:
                pipeline = list(pipeline)
                pipeline.insert(0, {"$match": spec})
        return super().aggregate(pipeline, **kwargs)


def _wrap_polymodel(
        cls: Type[P],
        name: str,
        value: Any,
        child_class: Type[P]) -> Type[P]:
    """ Wrap the child class and return it """
    child_class._name = cls._get_name()
    child_class._polyinfo = {
        "parent": cls,
        "name": name,
        "value": value
    }
    if cls._child_models is not None:
        cls._child_models[value] = child_class
    return child_class


def warn_about_keyword_deprecation(keyword: str) -> None:
    warnings.warn(
        "PyMongo has removed the '{}' keyword. Mogo disregards this "
        "keyword and in the near future will raise an error.".format(keyword),
        DeprecationWarning)


__all__ = ["Model", "PolyModel"]
