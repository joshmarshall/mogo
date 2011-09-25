"""
A variety of tests to cover the majority of the functionality
in mogo Fields.
"""

import unittest
from mogo import Field, ReferenceField

class Base(object):
    pass

class Sub(Base):
    pass

class MogoFieldTests(unittest.TestCase):

    def test_field(self):

        class MockModel(dict):
            field = Field(unicode)
            typeless = Field()
            required = Field(required=True)
            string = Field(basestring)
            reference = ReferenceField(Base)

        mock = MockModel()
        # checks if it is in the model fields (shouldn't be yet)
        self.assertRaises(AttributeError, getattr, mock, "field")

        # NOW we set up fields.
        cls_dict = MockModel.__dict__
        field_names = ["typeless", "required", "field", "string"]
        MockModel._fields = dict([(cls_dict[v].id, v) for v in field_names])
        self.assertEqual(mock.field, None)

        mock.field = u"testing"
        self.assertEqual(mock.field, "testing")
        self.assertEqual(mock["field"], "testing")
        self.assertRaises(TypeError, setattr, mock, "field", 5)
        mock.required = u"testing"
        self.assertEqual(mock["required"], "testing")

        # Testing type-agnostic fields
        mock = MockModel()
        # shouldn't raise anything
        mock.typeless = 5
        mock.typeless = "string"

        # Testing issubclass comparison for type checking
        # neither of these should raise a type error
        mock = MockModel(string="foobar")
        mock = MockModel(string=u"foobar")

        base = Base()
        sub = Sub()
        mock = MockModel(reference=base)
        mock = MockModel(reference=sub)
