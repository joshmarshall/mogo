from mogo.polymodel import PolyModel
from mogo.field import Field
import unittest


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


class MogoTestPolyModel(unittest.TestCase):

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
