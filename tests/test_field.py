"""
A variety of tests to cover the majority of the functionality
in mogo Fields.
"""

import unittest
from mogo import Field

class MogoFieldTests(unittest.TestCase):

    def test_field(self):
        results = {"field": None}

        class MockModel(dict):
            field = Field(unicode)
            typeless = Field()
            required = Field(required=True)

            def _update_field_value(self, field, value):
                results[field] = value

            def __getitem__(self, field):
                return results[field]


        mock = MockModel()
        # checks if it is in the model fields (shouldn't be yet)
        self.assertRaises(AttributeError, getattr, mock, "field")

        # NOW we set up fields.
        cls_dict = MockModel.__dict__
        field_names = ["typeless", "required", "field"]
        MockModel._fields = dict([(cls_dict[v].id, v) for v in field_names])
        self.assertIsNone(mock.field)

        mock.field = u"testing"
        self.assertEqual(mock.field, "testing")
        self.assertEqual(results["field"], "testing")
        self.assertRaises(TypeError, setattr, mock, "field", 5)
        mock.required = u"testing"
        self.assertEqual(results["required"], "testing")

        # Testing type-agnostic fields
        mock = MockModel()
        # shouldn't raise anything
        mock.typeless = 5
        mock.typeless = "string"
