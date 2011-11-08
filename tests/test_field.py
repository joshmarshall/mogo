"""
A variety of tests to cover the majority of the functionality
in mogo Fields.
"""

import unittest

import mogo
from mogo import Field

class MogoFieldTests(unittest.TestCase):

    def test_field(self):

        class MockModel(dict):
            field = Field(unicode)
            typeless = Field()
            required = Field(required=True)

        mock = MockModel()
        # checks if it is in the model fields (shouldn't be yet)
        self.assertRaises(AttributeError, getattr, mock, "field")

        # NOW we set up fields.
        cls_dict = MockModel.__dict__
        field_names = ["typeless", "required", "field"]
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

    def test_change_field_name(self):
        """It should allow an override of a field's name."""
        class MockModel(mogo.Model):
            abbreviated = Field(unicode, field_name="abrv")

        model = MockModel.new(abbreviated=u"lorem ipsum")

        # Check the model's dictionary.
        self.assertTrue("abrv" in model)
        # Access by friendly name.
        self.assertEqual(u"lorem ipsum", model.abbreviated)
        # No access by field_name.
        with self.assertRaises(AttributeError):
            model.abrv
