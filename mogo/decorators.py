"""
Just various decorators.
"""

class notinstancemethod(object):
    """ 
    Used to refuse access to a classmethod if called from 
    an instance.
    """
    
    def __init__(self, func):
        self.func = classmethod(func)
        
    def __get__(self, obj, objtype=None):
        if obj is not None:
            raise TypeError("Cannot call this method on an instance.")
        return self.func.__get__(obj, objtype)
