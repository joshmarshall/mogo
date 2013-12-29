from mogo.field import Field


class NewModelClass(type):
    """ Metaclass for inheriting field lists """

    def __new__(cls, name, bases, attributes):
        # Emptying fields by default
        attributes["_fields"] = {}
        new_model = super(NewModelClass, cls).__new__(
            cls, name, bases, attributes)
        # pre-populate fields
        new_model._update_fields()
        if hasattr(new_model, "_child_models"):
            # Resetting any model register for PolyModels -- better way?
            new_model._child_models = {}
        return new_model

    def __setattr__(cls, name, value):
        """ Catching new field additions to classes """
        super(NewModelClass, cls).__setattr__(name, value)
        if isinstance(value, Field):
            # Update the fields, because they have changed
            cls._update_fields()
