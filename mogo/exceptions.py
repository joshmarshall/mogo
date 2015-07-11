class InvalidUpdateCall(Exception):
    """ Raised whenever update is called on a new model """
    pass


class UnknownField(Exception):
    """ Raised whenever an invalid field is accessed and the
    AUTO_CREATE_FIELDS is False.
    """
    pass


class EmptyRequiredField(Exception):
    """ Raised when a required field is not set on the model instance. """
    pass
