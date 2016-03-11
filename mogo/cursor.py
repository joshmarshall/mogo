"""
Really, really basic around pymongo.Cursor. Just makes sure
that a result dict is wrapped in a Model to keep everything
clean.
"""

from pymongo.cursor import Cursor as PyCursor
from pymongo import ASCENDING, DESCENDING

# Shortcuts are better! :)
ASC = ASCENDING
DESC = DESCENDING


class Cursor(PyCursor):
    """ A simple wrapper around pymongo's Cursor class. """

    def __init__(self, model, spec=None, *args, **kwargs):
        self._order_entries = []
        self._query = spec
        self._model = model
        PyCursor.__init__(
            self, model._get_collection(), spec, *args, **kwargs)

    def next(self):
        value = PyCursor.next(self)
        return self._model(**value)

    # convenient because if it quacks like a list...
    def __len__(self):
        return self.count()

    def __getitem__(self, *args, **kwargs):
        value = PyCursor.__getitem__(self, *args, **kwargs)
        if type(value) == self.__class__:
            return value
        return self._model(**value)

    def first(self):
        if self.count() == 0:
            return None
        return self[0]

    def order(self, **kwargs):
        if len(kwargs) != 1:
            raise ValueError("order() requires one field = ASC or DESC.")
        for key, value in kwargs.iteritems():
            if value not in (ASC, DESC):
                raise TypeError("Order value must be mogo.ASC or mogo.DESC.")
            self._order_entries.append((key, value))
            # According to the docs, only the LAST .sort() matters to
            # pymongo, so this SHOULD be safe
            self.sort(self._order_entries)
        return self

    def update(self, modifier):
        if self._query is None:
            raise ValueError(
                "Cannot update on a cursor without a query. If you "
                "actually want to modify all values on a model, pass "
                "in an explicit {} to find().")
        self._model.update(self._query, modifier, multi=True)
        return self

    def change(self, **kwargs):
        modifier = {"$set": kwargs}
        return self.update(modifier)
