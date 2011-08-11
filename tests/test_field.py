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
            field = Field()
            required = Field(required=True)

            def _update_field_value(self, field, value):
                results[field] = value

            def __getitem__(self, field):
                return results[field]

        mock = MockModel()
        self.assertRaises(AttributeError, getattr, mock, "field")
        field_obj = mock.__class__.__dict__["field"]
        field_id = id(field_obj)
        required_obj = mock.__class__.__dict__["required"]
        required_id = id(required_obj)
        mock._fields = { field_id: "field", required_id: "required" }
        self.assertIsNone(mock.field)
        mock.field = u"testing"
        self.assertEqual(mock.field, "testing")
        self.assertEqual(results["field"], "testing")
        self.assertRaises(TypeError, setattr, mock, "field", 5)
        mock.required = u"testing"
        self.assertEqual(results["required"], "testing")
