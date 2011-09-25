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
        self._set_callback = kwargs.get("set_callback")
        self._get_callback = kwargs.get("get_callback")
        self.id = id(self)

    def __get__(self, instance, klass=None):
        if instance is None:
            # Classes see the descriptor itself
            return self
        value = self._get_value(instance)
        return value

    def _get_field_name(self, instance):
        """ Try to retrieve field name from instance """
        fields = getattr(instance, "_fields")
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
            value = self._get_callback(value)
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
            value = self._set_callback(value)
        field_name = self._get_field_name(instance)
        instance[field_name] = value


class ReferenceField(Field):
    """ Simply holds information about the reference model. """

    def __init__(self, model, **kwargs):
        kwargs.setdefault("set_callback", self._set_callback)
        kwargs.setdefault("get_callback", self._get_callback)
        super(ReferenceField, self).__init__(model, **kwargs)
        self.model = model

    def _set_callback(self, value):
        """ Resolves a Model to a DBRef """
        if value:
            value = DBRef(self.model._get_name(), value.id)
        return value

    def _get_callback(self, value):
        """ Retrieves the id, then retrieves the model from the db """
        if value:
            # Should be a DBRef
            return self.model.find_one({"_id": value.id})
        return value
