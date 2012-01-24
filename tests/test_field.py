"""
A variety of tests to cover the majority of the functionality
in mogo Fields.
"""

import unittest
from mogo import Field, ReferenceField, connect, Model, EnumField

class Base(object):
    pass

class Sub(Base):
    pass


class MogoFieldTests(unittest.TestCase):

    def setUp(self):
        super(MogoFieldTests, self).setUp()
        self._mongo_connection = connect("__test_change_field_name")

    def tearDown(self):
        super(MogoFieldTests, self).tearDown()
        self._mongo_connection.drop_database("__test_change_field_name")
        self._mongo_connection.disconnect()

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

    def test_change_field_name(self):
        """It should allow an override of a field's name."""
        class MockModel(Model):
            abbreviated = Field(unicode, field_name="abrv")
            long_name = Field(unicode, field_name="ln", required=True)
            regular = Field(unicode, required=True)

        model = MockModel(abbreviated=u"lorem ipsum",
            long_name=u"malarky", regular=u"meh.")

        # Check the model's dictionary.
        self.assertTrue("abrv" in model)
        # Access by friendly name.
        self.assertEqual(u"lorem ipsum", model.abbreviated)
        # No access by field_name.
        with self.assertRaises(AttributeError):
            model.abrv

        # Test save.
        model.save(safe=True)

        # Test search.
        fetched = MockModel.search(abbreviated=u"lorem ipsum")
        self.assertIsNotNone(fetched)
        fetched = MockModel.search(long_name=u"malarky")
        self.assertIsNotNone(fetched)

        # Test updates with long names.
        model.update(abbreviated=u"dolor set")
        self.assertEqual(u"dolor set", model.abbreviated)
        fetched = MockModel.search(abbreviated=u"dolor set")
        self.assertEqual(1, fetched.count())

        model.update(long_name=u"foobar")
        self.assertEqual(u"foobar", model.long_name)
        fetched = MockModel.search(long_name=u"foobar")
        self.assertEqual(1, fetched.count())

        # Test updates with short names.
        MockModel.update({}, {"$set": {"abrv": u"revia"}})
        fetched = MockModel.find_one({"abrv": "revia"})
        self.assertEqual(fetched.abbreviated, "revia")

        # Test finds with short names.
        fetched = MockModel.find({"ln": "foobar"})
        self.assertEqual(1, fetched.count())
        fetched = fetched.first()
        self.assertEqual(u"revia", fetched.abbreviated)

        # Test search on regular fields.
        fetched = MockModel.search(regular=u"meh.")
        self.assertEqual(1, fetched.count())

    def test_enum_field(self):
        """ Test the enum field """
        class EnumModel1(Model):
            field = EnumField((1, 3, "what"))

        instance = EnumModel1(field=3)
        self.assertEqual(instance.field, 3)
        with self.assertRaises(ValueError):
            instance = EnumModel1(field=False)

        class EnumModel2(Model):
            field = EnumField(lambda x: x.__class__.__name__)
        EnumModel2(field="EnumModel2")
        with self.assertRaises(ValueError):
            EnumModel1(field="nottheclassname")

