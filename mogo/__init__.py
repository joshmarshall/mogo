""" This is the mogo syntactic sugar library for MongoDB. """

from mogo.model import Model, PolyModel
from mogo.field import Field, ReferenceField, ConstantField, EnumField
from mogo.cursor import ASC, DESC
from mogo.connection import connect, session

# Allows flexible (probably dangerous) automatic field creation for
# /really/ schemaless designs.
AUTO_CREATE_FIELDS = False

__all__ = ['Model', 'PolyModel', 'Field', 'ReferenceField', "ConstantField",
    "EnumField", 'connect', 'session', 'ASC', 'DESC', "AUTO_CREATE_FIELDS"]
