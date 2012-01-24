""" The basic field attributes. """

from pymongo.dbref import DBRef

class EmptyRequiredField(Exception):
    """ Raised when a required field is not set on the model instance. """
    pass

class Field(object):
    """
    This class may eventually do type-checking, default values,
    etc. but for right now it's for subclassing and glorified
    documentation.
    """

    default = None
    value_type = None

    def __init__(self, value_type=None, **kwargs):
        self.value_type = value_type
        self.required = kwargs.get("required", False) is True
        self.default = kwargs.get("default", None)
        set_callback = getattr(self, "_set_callback", None)
        get_callback = getattr(self, "_get_callback", None)
        self._set_callback = kwargs.get("set_callback", set_callback)
        self._get_callback = kwargs.get("get_callback", get_callback)
        self.id = id(self)
        self._field_name = kwargs.get("field_name", None)

    def __get__(self, instance, klass=None):
        if instance is None:
            # Classes see the descriptor itself
            return self
        value = self._get_value(instance)
        return value

    def _get_field_name(self, model_instance):
        """ Try to retrieve field name from instance """
        if self._field_name:
            return self._field_name
        fields = getattr(model_instance, "_fields")
        return fields[self.id]

    def _get_value(self, instance):
        """ Retrieve the value from the instance """
        field_name = self._get_field_name(instance)
        if not instance.has_key(field_name):
            if self.required:
                raise EmptyRequiredField("'%s' is required but is empty."
                                         % field_name)
            else:
                instance[field_name] = self._get_default()
        value = instance[field_name]
        if self._get_callback:
            value = self._get_callback(instance, value)
        return value

    def _get_default(self):
        """ Retrieve the default value and return it """
        if callable(self.default):
            return self.default()
        else:
            return self.default

    def _check_value_type(self, value):
        """ Verifies that a value is the proper type """
        if value is not None and self.value_type is not None:
            valid = isinstance(value, self.value_type)
            if not valid:
                return False
        return True

    def __set__(self, instance, value):
        value_type = type(value)
        if not self._check_value_type(value):
            raise TypeError("Invalid type %s instead of %s" %
                (value_type, self.value_type)
            )
        if self._set_callback:
            value = self._set_callback(instance, value)
        field_name = self._get_field_name(instance)
        instance[field_name] = value


class ReferenceField(Field):
    """ Simply holds information about the reference model. """

    def __init__(self, model, **kwargs):
        super(ReferenceField, self).__init__(model, **kwargs)
        self.model = model

    def _set_callback(self, instance, value):
        """ Resolves a Model to a DBRef """
        if value:
            value = DBRef(self.model._get_name(), value.id)
        return value

    def _get_callback(self, instance, value):
        """ Retrieves the id, then retrieves the model from the db """
        if value:
            # Should be a DBRef
            return self.model.find_one({"_id": value.id})
        return value

class ConstantField(Field):
    """ Doesn't let you change the value after setting it. """

    def _set_callback(self, instance, value):
        """ Block changing values from being set. """
        if instance._get_id() and value is not self._get_value(instance):
            raise ValueError("Constant fields cannot be altered after saving.")
        return value


class EnumField(Field):
    """ Only accepts values from a set / list of values.
    The first argument should be an iterable with acceptable values, or
    optionally a callable that takes the instance as the first argument and
    returns an iterable with acceptable values.

    For instance, both of these are valid:

        EnumField(("a", "b", 5))
        EnumField(lambda x: [5, 6])

    """

    def __init__(self, iterable, **kwargs):
        super(EnumField, self).__init__(**kwargs)
        self.iterable = iterable

    def _set_callback(self, instance, value):
        """ Checks for value in iterable. """
        accepted_values = self.iterable
        if callable(self.iterable):
            accepted_values = self.iterable(instance)
        if value not in accepted_values:
            # not listing the accepted values because that might be bad,
            # for example, if it's a cursor or other exhaustible iterator
            raise ValueError("Value %s not in acceptable values." % value)
        return value
