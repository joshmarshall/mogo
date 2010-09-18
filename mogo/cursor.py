""" 
Really, really basic around pymongo.Cursor. Just makes sure
that a result dict is wrapped in a Model to keep everything
clean.
"""

from pymongo.cursor import Cursor as PyCursor

class Cursor(PyCursor):
    """ A simple wrapper around pymongo's Cursor class. """
    
    def __init__(self, model, *args, **kwargs):
        self._model = model
        PyCursor.__init__(self, model._get_collection(), *args, **kwargs)
        
    def next(self):
        value = PyCursor.next(self)
        return self._model(**value)
        
    def __getitem__(self, index):
        value = PyCursor.__getitem__(self, index)
        return self._model(**value)