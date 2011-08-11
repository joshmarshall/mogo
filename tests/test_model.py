""" Various tests for the Model class """

from mogo.model import Model, UseModelNewMethod
from mogo.field import ReferenceField, Field, EmptyRequiredField
import unittest


class MockCollection(object):
    pass

class Ref(Model):
    pass

class Foo(Model):

    _collection = MockCollection()

    field = Field()
    required = Field(required=True)
    callback = Field(get_callback=lambda x: "foo",
                     set_callback=lambda x: "bar")
    reference = ReferenceField(Ref)
    _ignore_me = Field()


class MogoTestModel(unittest.TestCase):

    def test_model_fields_init(self):
        """ Test that the model properly retrieves the fields """
        foo = Foo.new()
        self.assertTrue("field" in foo._fields.values())
        self.assertTrue("required" in foo._fields.values())
        self.assertTrue("callback" in foo._fields.values())
        self.assertTrue("reference" in foo._fields.values())
        self.assertFalse("_ignore_me" in foo._fields.values())
        self.assertEqual(len(foo._updated), 0)

    def test_update_fields(self):
        foo = Foo.new()
        self.assertEqual(len(foo._updated), 0)
        foo._update_field_value("field", "testing")
        self.assertEqual(foo._updated, ["field"])

    def test_get_updated(self):
        foo = Foo.new(bar=u"testing")
        foo.required = u"required"
        updated = foo._get_updated()
        self.assertEqual(updated, foo.copy())

    def test_required_fields(self):
        foo = Foo.new()
        self.assertRaises(EmptyRequiredField, foo.save)
        self.assertRaises(EmptyRequiredField, getattr, foo, "required")

    def test_initializing_from_constructor(self):
        self.assertRaises(UseModelNewMethod, Foo)

    def test_new_constructor(self):
        foo1 = Foo.new()
        foo2 = Foo.new()
        foo1.bar = u"testing"
        foo2.bar = u"whatever"
        self.assertNotEqual(foo1.bar, foo2.bar)

    def test_null_reference(self):
        foo = Foo.new()
        foo.reference = None
        self.assertEqual(foo.reference, None)

    def test_repr(self):
        foo = Foo.new()
        foo["_id"] = 5
        self.assertEqual(str(foo), "<MogoModel:foo id:5>")
