import inspect

class Field(object):
    """
    This class may eventually do type-checking, default values,
    etc. but for right now it's for subclassing and glorified
    documentation.
    """

    default = None
    value_type = None

    def __init__(self, value_type=None, default=None):
        self.default = default
        if value_type == None:
            value_type = str
        self.value_type = value_type

class ReferenceField(Field):
    """ Simply holds information about the reference model. """

    def __init__(self, model):
        self.model = model
