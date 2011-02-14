import inspect

class Field(object):
    """ 
    This class may eventually do type-checking, default values,
    etc. but for right now it's for subclassing and glorified
    documentation.
    """
    
    default = None
    strict_type = None
    
    def __init__(self, strict_type=None, default=None):
        if default != None:
            raise NotImplementedError(
                "Default values not yet implemented."
            )
        if strict_type != None:
            raise NotImplementedError(
                "Strict typing has not yet beeen implemented."
            )
        
class ReferenceField(Field):
    """ Simply holds information about the reference model. """
    
    def __init__(self, model):
        self.model = model
