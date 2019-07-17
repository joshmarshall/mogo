""" The basic field attributes. """

from bson.dbref import DBRef

from typing import Any, Callable, cast, Generic, Optional
from typing import Sequence, Type, TypeVar, TYPE_CHECKING, Union


S = TypeVar("S")  # serialized type
T = TypeVar("T")  # interface type

_DefaultCallback = Callable[[], T]
_SetCallback = Callable[["Model", Optional[T]], Any]
_GetCallback = Callable[["Model", Any], Optional[T]]
_CoerceCallback = Callable[[Any], Optional[T]]


class EmptyRequiredField(Exception):
    """ Raised when a required field is not set on the model instance. """
    pass


class NoDefaultValue(Exception):
    pass


class _NoDefault(object):
    pass


NO_DEFAULT = _NoDefault()  # type: _NoDefault


_DefaultOptions = Union[_NoDefault, _DefaultCallback[T], T]


class Field(Generic[T]):
    """
    This class is responsible for type-checking, set- and get- callbacks,
    coercing values, and general data-y things. More simply, it is responsible
    for storing things into mongo-friendly values and retrieving them in
    application-friendly values.
    """

    value_type = None  # type: Optional[Type[T]]
    id = 0  # type: int
    _field_name = None  # type: Optional[str]
    __set_callback = None  # type: Optional[_SetCallback[T]]
    __get_callback = None  # type: Optional[_GetCallback[T]]
    __coerce_callback = None  # type: Optional[_CoerceCallback[T]]
    __default = None  # type: Optional[_DefaultOptions[T]]
    __required = False  # type: bool

    def __init__(
            self,
            value_type: Optional[Type[T]] = None,
            required: bool = False,
            set_callback: Optional[_SetCallback[T]] = None,
            get_callback: Optional[_GetCallback[T]] = None,
            coerce_callback: Optional[_CoerceCallback[T]] = None,
            field_name: Optional[str] = None,
            default: Optional[_DefaultOptions[T]] = NO_DEFAULT,
            **kwargs: Any) -> None:
        self.value_type = value_type or self.value_type
        self._field_name = field_name
        self.__required = required
        self.__set_callback = set_callback
        self.__get_callback = get_callback
        self.__coerce_callback = coerce_callback
        self.__default = default
        self.id = id(self)

    def __get__(
            self,
            instance: "Model",
            klass: Optional[Type["Model"]] = None) -> \
            Union['Field[T]', Any]:
        if instance is None:
            # Classes see the descriptor itself
            return self
        value = self._get_value(instance)
        return value

    def _get_default(self) -> T:
        if self.__default == NO_DEFAULT:
            raise NoDefaultValue("No default value for field")
        if not callable(self.__default):
            return cast(T, self.__default)
        else:
            return self.__default()

    def _get_field_name(self, model_instance: "Model") -> str:
        """ Try to retrieve field name from instance """
        if self._field_name:
            return self._field_name
        return model_instance._get_fields()[self.id]

    def _get_value(self, instance: "Model") -> Optional[T]:
        """ Retrieve the value from the instance """
        field_name = self._get_field_name(instance)
        if field_name not in instance:
            if self._is_required():
                raise EmptyRequiredField(
                    "'{}' is required but is empty.".format(field_name))
            self._set_default(instance, field_name)
        value = self.get_callback(instance, instance.get(field_name))
        return value

    def _set_default(self, model: "Model", field: str) -> None:
        if field in model:
            # value already set, not overwriting it.
            return
        try:
            setattr(model, field, self._get_default())
        except NoDefaultValue:
            pass

    def _is_required(self) -> bool:
        return self.__required

    def _check_value_type(self, value: Any, field_name: str) -> None:
        """ Verifies that a value is the proper type """
        if value is not None and self.value_type is not None:
            valid = isinstance(value, self.value_type)
            if not valid:
                value_type = type(value)
                raise TypeError(
                    "Invalid type {} instead of {} for field '{}'".format(
                        value_type, self.value_type, field_name))

    def __set__(self, instance: "Model", value: Any) -> None:
        field_name = self._get_field_name(instance)
        try:
            self._check_value_type(value, field_name)
        except TypeError:
            value = self.coerce_callback(value)
            self._check_value_type(value, field_name)

        value = self.set_callback(instance, value)
        instance[field_name] = value

    # The Field.X_callback methods are always called, and they are simply
    # responsible for delegating whether to call the default (sub)class'
    # `_X_callback` method, or the custom methods provided at instantiation.

    def get_callback(
            self, instance: "Model",
            value: Optional[Any]) -> Optional[T]:
        if self.__get_callback is not None:
            return self.__get_callback(instance, value)
        return self._get_callback(instance, value)

    def set_callback(
            self, instance: "Model",
            value: Optional[T]) -> Optional[Any]:
        if self.__set_callback is not None:
            return self.__set_callback(instance, value)
        return self._set_callback(instance, value)

    def coerce_callback(self, value: Any) -> Optional[T]:
        if self.__coerce_callback is not None:
            return self.__coerce_callback(value)
        return self._coerce_callback(value)

    # these are overwritten by the individual subclasses of Field, and are
    # called when no custom `X_callback` is specified on field construction.

    def _get_callback(
            self, instance: "Model",
            value: Any) -> Optional[T]:
        return cast(Optional[T], value)

    def _set_callback(
            self, instance: "Model",
            value: Optional[T]) -> Any:
        return value

    def _coerce_callback(self, value: Any) -> Optional[T]:
        return cast(Optional[T], value)


class ReferenceField(Field["Model"]):
    """ Simply holds information about the reference model. """

    def __init__(self, model: Type["Model"], **kwargs: Any) -> None:
        super().__init__(value_type=model, **kwargs)
        self.model = model

    def _set_callback(
            self, instance: "Model",
            value: Optional["Model"]) -> \
            Optional[DBRef]:
        """ Resolves a Model to a DBRef """
        if value is None:
            return None
        dbref = DBRef(self.model._get_name(), value.id)
        return dbref

    def _get_callback(
            self, instance: "Model",
            value: Optional[DBRef]) -> \
            Optional["Model"]:
        """ Retrieves the id, then retrieves the model from the db """
        if value is not None:
            # Should be a DBRef
            return self.model.find_one({"_id": value.id})
        return None


class ConstantField(Field[Any]):
    """ Doesn't let you change the value after setting it. """

    def _set_callback(self, instance: "Model", value: Any) -> Any:
        """ Block changing values from being set. """
        if instance._get_id() and value is not self._get_value(instance):
            raise ValueError("Constant fields cannot be altered after saving.")
        return value


_EnumCallback = Callable[["Model"], Sequence[T]]
_EnumOptions = Union[Sequence[T], _EnumCallback[T]]


class EnumField(Field[S]):
    """ Only accepts values from a set / list of values.
    The first argument should be an iterable with acceptable values, or
    optionally a callable that takes the instance as the first argument and
    returns an iterable with acceptable values.

    For instance, both of these are valid:

        EnumField(("a", "b", 5))
        EnumField(lambda x: [5, 6])

    """

    iterable = []  # type: _EnumOptions[S]

    def __init__(self, iterable: _EnumOptions[S], **kwargs: Any) -> None:
        super(EnumField, self).__init__(**kwargs)
        self.iterable = iterable

    def _set_callback(
            self, instance: "Model",
            value: Optional[S]) -> Optional[S]:
        """ Checks for value in iterable. """
        accepted_values = []  # type: Sequence[S]
        if callable(self.iterable):
            accepted_values = self.iterable(instance)
        else:
            accepted_values = self.iterable
        if value not in accepted_values:
            # not listing the accepted values because that might be bad,
            # for example, if it's a cursor or other exhaustible iterator
            raise ValueError(
                "Value {} not in acceptable values.".format(value))
        return value


if TYPE_CHECKING:
    from mogo.model import Model


__all__ = ["Field", "ReferenceField", "ConstantField", "EnumField"]
