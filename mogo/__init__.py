""" This is the mogo syntactic sugar library for MongoDB. """

from mogo.model import Model, PolyModel
from mogo.field import Field, ReferenceField
from mogo.cursor import ASC, DESC
from mogo.connection import connect

# Allows flexible (probably dangerous) automatic field creation for
# /really/ schemaless designs.
AUTO_CREATE_FIELDS = False

__all__ = ['Model', 'PolyModel', 'Field', 'ReferenceField', 'connect',
           'ASC', 'DESC', "AUTO_CREATE_FIELDS"]
