"""
A variety of tests to cover the majority of the functionality
in mogo Fields.
"""

import unittest
from mogo import Field, ReferenceField, connect, Model, EnumField
from mogo.field import EmptyRequiredField

from typing import Any, cast, Optional, Sequence


class Base(Model):
    pass


class Sub(Base):
    pass


class MogoFieldTests(unittest.TestCase):

    def setUp(self) -> None:
        super(MogoFieldTests, self).setUp()
        self._mongo_connection = connect("__test_change_field_name")

    def tearDown(self) -> None:
        super(MogoFieldTests, self).tearDown()
        self._mongo_connection.drop_database("__test_change_field_name")
        self._mongo_connection.close()

    def test_field(self) -> None:

        class MockModel(Model):
            field = Field[str](str)
            typeless = Field[Any]()
            required = Field[Any](required=True)
            string = Field[str](str)
            reference = ReferenceField(Base)

        mock = MockModel()
        self.assertEqual(mock.field, None)

        mock.field = "testing"
        self.assertEqual(mock.field, "testing")
        self.assertEqual(mock["field"], "testing")
        self.assertRaises(TypeError, setattr, mock, "field", 5)
        mock.required = "testing"
        self.assertEqual(mock["required"], "testing")

        # Testing type-agnostic fields
        mock = MockModel()
        # shouldn't raise anything
        mock.typeless = 5
        mock.typeless = "string"

        # Testing issubclass comparison for type checking
        # neither of these should raise a type error
        mock = MockModel(string="foobar")
        mock = MockModel(string="foobar")

        base = Base()
        sub = Sub()
        mock = MockModel(reference=base)
        mock = MockModel(reference=sub)

        empty_model = MockModel()
        # testing that the required field is, you know, required.
        self.assertRaises(EmptyRequiredField, getattr, empty_model, "required")

    def test_change_field_name(self) -> None:
        """It should allow an override of a field's name."""
        class MockModel(Model):
            abbreviated = Field[str](str, field_name="abrv")
            long_name = Field[str](str, field_name="ln", required=True)
            regular = Field[str](str, required=True)

        model = MockModel(
            abbreviated="lorem ipsum", long_name="malarky", regular="meh.")

        # Check the model's dictionary.
        self.assertIn("abrv", model)
        # Access by friendly name.
        self.assertEqual("lorem ipsum", model.abbreviated)
        # No access by field_name.
        self.assertRaises(AttributeError, getattr, model, "abrv")

        # Test save.
        model.save()

        # Test search.
        fetched = MockModel.search(abbreviated="lorem ipsum")
        self.assertIsNotNone(fetched)
        fetched = MockModel.search(long_name="malarky")
        self.assertIsNotNone(fetched)

        # Test updates with long names.
        model.update(abbreviated="dolor set")
        self.assertEqual("dolor set", model.abbreviated)
        fetched = MockModel.search(abbreviated="dolor set")
        self.assertEqual(1, fetched.count())

        model.update(long_name="foobar")
        self.assertEqual("foobar", model.long_name)
        fetched = MockModel.search(long_name="foobar")
        self.assertEqual(1, fetched.count())

        # Test updates with short names.
        MockModel.update({}, {"$set": {"abrv": "revia"}})  # type: ignore
        fetched_one = MockModel.find_one({"abrv": "revia"})
        if fetched_one is None:
            self.fail("Find one result should not be None.")
        else:
            self.assertEqual(fetched_one.abbreviated, "revia")

        # Test finds with short names.
        fetched = MockModel.find({"ln": "foobar"})
        self.assertEqual(1, fetched.count())
        fetched_result = fetched.first()
        if fetched_result is None:
            self.fail("First result should not be None.")
        self.assertEqual("revia", fetched_result.abbreviated)

        # Test search on regular fields.
        fetched = MockModel.search(regular="meh.")
        self.assertEqual(1, fetched.count())

    def test_enum_field(self) -> None:
        """ Test the enum field """
        class EnumModel1(Model):
            field = EnumField((1, 3, "what"))

        instance = EnumModel1(field=3)
        self.assertEqual(instance.field, 3)
        with self.assertRaises(ValueError):
            instance = EnumModel1(field=False)

        class EnumModel2(Model):
            field = EnumField(
                lambda x: cast(Sequence[str], x.__class__.__name__))
        EnumModel2(field="EnumModel2")
        with self.assertRaises(ValueError):
            EnumModel1(field="nottheclassname")

    def test_default_field(self) -> None:
        """ Test that the default behavior works like you'd expect. """
        class TestDefaultModel(Model):
            field = Field[Any]()  # i.e. no default value

        entry = TestDefaultModel()
        self.assertNotIn("field", entry)

        self.assertIsNone(entry.field)
        self.assertNotIn("field", entry)

        class TestDefaultModel2(Model):
            field = Field[Any](default=None)

        entry2 = TestDefaultModel2()
        self.assertIn("field", entry2)
        self.assertIsNone(entry2.field)
        self.assertIsNone(entry2["field"])

        entry3 = TestDefaultModel2(field="foobar")
        self.assertEqual("foobar", entry3.field)
        self.assertEqual("foobar", entry3["field"])

    def test_field_coercion(self) -> None:

        class FloatField(Field[float]):
            value_type = float

            def _coerce_callback(self, value: Optional[Any]) -> float:
                if value is not None:
                    return float(value)
                return 0.0

        class TestCoerceModel(Model):
            percent = FloatField()

        model = TestCoerceModel(percent=100)
        self.assertEqual(float, type(model["percent"]))

        model = TestCoerceModel(percent=99.5)
        self.assertEqual(float, type(model["percent"]))

        class TestCoerceModel2(Model):
            percent = Field[float](
                float, coerce_callback=lambda x: int(x))

        with self.assertRaises(TypeError):
            TestCoerceModel2(percent=2)
