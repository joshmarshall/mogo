""" This is the mogo syntactic sugar library for MongoDB. """

from mogo.model import *  # noqa: F403,F401
from mogo.field import *  # noqa: F403,F401
from mogo.cursor import *  # noqa: F403,F401
from mogo.connection import *  # noqa: F403,F401

# Allows flexible (probably dangerous) automatic field creation for
# /really/ schemaless designs.
AUTO_CREATE_FIELDS = False


__all__ = [  # noqa: F405
    "Model",
    "PolyModel",
    "ConstantField",
    "Field",
    "ReferenceField",
    "EnumField",
    "connect",
    "session",
    "DESC",
    "ASC",
]
