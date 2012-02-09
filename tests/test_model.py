""" Various tests for the Model class """

import mogo
from mogo.model import PolyModel, Model, InvalidUpdateCall, UnknownField
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
    default = Field(default="default")
    callback = Field(get_callback=lambda x, y: "foo",
                     set_callback=lambda x, y: "bar")
    reference = ReferenceField(Ref)
    _private_field = Field()


class Bar(Model):

    uid = Field(unicode)

class ChildRef(Ref):
    pass

class Person(PolyModel):

    @classmethod
    def get_child_key(cls):
        return "role"

    role = Field(unicode, default=u"person")

    def walk(self):
        """ Default method """
        return True

@Person.register
class Child(Person):
    role = Field(unicode, default=u"child")

@Person.register(name="infant")
class Infant(Person):
    age = Field(int, default=3)

    def crawl(self):
        """ Example of a custom method """
        return True

    def walk(self):
        """ Overwriting a method """
        return False

class MogoTestModel(unittest.TestCase):

    def test_model_fields_init(self):
        """ Test that the model properly retrieves the fields """
        foo = Foo()
        self.assertTrue("field" in foo._fields.values())
        self.assertTrue("required" in foo._fields.values())
        self.assertTrue("callback" in foo._fields.values())
        self.assertTrue("reference" in foo._fields.values())
        self.assertTrue("default" in foo._fields.values())
        self.assertTrue("_private_field" in foo._fields.values())

    def test_model_create_fields_init(self):
        """ Test that the model creates fields that don't exist """
        class Testing(Model):
            pass
        try:
            mogo.AUTO_CREATE_FIELDS = True
            schemaless = Testing(foo="bar")
            self.assertEqual(schemaless["foo"], "bar")
            self.assertEqual(schemaless.foo, "bar")
            self.assertTrue("foo" in schemaless.copy())
            foo_field = getattr(Testing, "foo")
            self.assertTrue(foo_field != None)
            self.assertTrue(id(foo_field) in schemaless._fields)
        finally:
            mogo.AUTO_CREATE_FIELDS = False

    def test_model_add_field(self):
        """ Tests the ability to add a field. """
        class Testing(Model):
            pass
        Testing.add_field("foo", Field(unicode,
            set_callback=lambda x, y: u"bar"))
        self.assertTrue(isinstance(Testing.foo, Field))
        testing = Testing(foo=u"whatever")
        self.assertEqual(testing["foo"], u"bar")
        self.assertEqual(testing.foo, u"bar")
        # TODO: __setattr__ behavior

    def test_model_fail_to_create_fields_init(self):
        """ Test that model does NOT create new fields """
        class Testing(Model):
            pass
        self.assertRaises(UnknownField, Testing, foo="bar")

    def test_default_field(self):
        foo = Foo()
        self.assertEqual(foo["default"], "default")
        self.assertEqual(foo.default, "default")

    def test_required_fields(self):
        foo = Foo()
        self.assertRaises(EmptyRequiredField, foo.save)
        self.assertRaises(EmptyRequiredField, getattr, foo, "required")
        self.assertRaises(InvalidUpdateCall, foo.update, foo=u"bar")

    def test_null_reference(self):
        foo = Foo()
        foo.reference = None
        self.assertEqual(foo.reference, None)

    def test_repr(self):
        foo = Foo()
        foo["_id"] = 5
        self.assertEqual(str(foo), "<MogoModel:foo id:5>")

    def test_reference_subclass(self):
        foo = Foo()
        child_ref = ChildRef(_id="testing") # hardcoding id
        foo.reference = child_ref
        self.assertEqual(foo["reference"].id, child_ref.id)

    def test_id(self):
        foo = Foo(_id="whoop")
        self.assertEqual(foo.id, "whoop")
        self.assertEqual(foo._id, "whoop")
        self.assertEqual(foo['_id'], "whoop")


    def test_inheritance(self):
        self.assertEqual(Person._get_name(), Child._get_name())
        self.assertEqual(Person._get_name(), Infant._get_name())
        person = Person()
        self.assertTrue(isinstance(person, Person))
        self.assertTrue(person.walk())
        self.assertEqual(person.role, "person")
        with self.assertRaises(AttributeError):
            person.crawl()
        child = Person(role=u"child")
        self.assertTrue(isinstance(child, Child))
        child2 = Child()
        self.assertTrue(child2.walk())
        self.assertEqual(child2.role, "child")
        child3 = Child(role=u"person")
        self.assertTrue(isinstance(child3, Person))

        infant = Infant()
        self.assertTrue(isinstance(infant, Infant))
        self.assertEqual(infant.age, 3)
        self.assertTrue(infant.crawl())
        self.assertFalse(infant.walk())
        infant2 = Person(age=3, role=u"infant")
        self.assertTrue(isinstance(infant2, Infant))
