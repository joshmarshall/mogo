"""
A variety of tests to cover the majority of the functionality
in mogo. I'd really like to get this to 100% code coverage...

NOTES:
I use safe=True for most of the save operations because sometimes
it was too quick and a find or search operation performed immediately
afterwards would not return the new object.

You need to have mongod running on the local machine for this
to run. Will probably add config options later for testing
remote machines.

If for some reason you have a database named "_mogotest", you will
probably want to change DBNAME. :)
"""

import unittest
import mogo
from mogo import PolyModel, Model, Field, ReferenceField, DESC, connect
from mogo import ConstantField
from mogo.connection import Connection
import pymongo
import pymongo.objectid
import sys
from datetime import datetime

DBNAME = '_mogotest'
ALTDB = "_mogotest2"
DELETE = True

class Foo(Model):
    bar = Field(unicode)
    typeless = Field()
    dflt = Field(unicode, default=u'dflt')
    callme = Field(unicode, default=lambda: u'funtimes')
    dtnow = Field(datetime, default=lambda: datetime.now())

    def __unicode__(self):
        return "FOOBAR"

Foo.ref = ReferenceField(Foo)

class FooWithNew(Model):
    bar = Field(unicode)

    @classmethod
    def new(cls):
        return cls(bar=u"whatever")

class Company(Model):
    name = Field(str)

    @property
    def people(self):
        return Person.search(company=self)

class Person(Model):
    _name = "people"
    company = ReferenceField(Company)
    name = Field(str)
    email = Field(str)

class SubPerson(Person):
    """ Testing inheritance """
    another_field = Field(str)


class Car(PolyModel):
    """ Base model for alternate inheritance """
    doors = Field(int, default=4)
    wheels = Field(int, default=4)
    type = Field(unicode, default=u"car")

    @classmethod
    def get_child_key(cls):
        return "type"

    def drive(self):
        """ Example method to overwrite """
        raise NotImplementedError("Implement this in child classes")

@Car.register("sportscar")
class SportsCar(Car):
    """ Alternate car """
    doors = Field(int, default=2)
    type = Field(unicode, default=u"sportscar")

    def drive(self):
        """ Overwritten """
        return True

@Car.register
class Convertible(SportsCar):
    """ New methods """

    _top_down = False

    type = Field(unicode, default=u"convertible")

    def toggle_roof(self):
        """ Opens / closes roof """
        self._top_down = not self._top_down
        return self._top_down

class MogoTests(unittest.TestCase):

    def setUp(self):
        self._conn = connect(DBNAME)

    def test_connect(self):
        self.assertTrue(isinstance(self._conn, pymongo.Connection))
        connection = Connection.instance()
        self.assertTrue(connection._database == DBNAME)
        self._conn.disconnect()

    def test_model(self):
        foo = Foo(bar=u'cheese')
        self.assertTrue(foo.bar == u'cheese')
        self.assertTrue(foo.dflt == u'dflt')
        self.assertTrue(foo.callme == u'funtimes')
        self.assertTrue(isinstance(foo.dtnow, datetime))
        foo.bar = u'model'
        self.assertTrue(foo.bar == u'model')

    def test_model_create(self):
        foo = Foo.create(bar=u"cheese")
        self.assertEqual(foo.bar, "cheese")
        self.assertEqual(Foo.find().count(), 1)
        # testing with a classmethod "new" defined.
        foo = FooWithNew.create()
        self.assertIsNotNone(foo._id)
        self.assertEqual(foo.bar, u"whatever")

    def test_save_defaults(self):
        """
        test that default values get saved alongside other values when creating
        the model.
        """
        foo = Foo(bar=u'goat')
        id_ = foo.save(safe=True)
        raw_result = Foo._collection.find_one({"_id": id_})
        self.assertTrue(raw_result["dflt"] == u'dflt')

    def test_create_delete(self):
        foo = Foo()
        foo.bar = u'create_delete'
        idval = foo.save(safe=True)
        self.assertTrue(type(idval) is pymongo.objectid.ObjectId)
        self.assertTrue(foo.id == idval)

    def test_search_or_create(self):
        foo = Foo.search_or_create(bar=u'howdy')
        self.assertIsInstance(foo._id, pymongo.objectid.ObjectId)
        foo.typeless = 4
        foo.save()

        baz = Foo.search_or_create(bar=u'howdy', typeless=2)
        self.assertNotEqual(foo.id,baz.id)
        self.assertEqual(baz.typeless, 2)

        qux = Foo.search_or_create(bar=u'howdy', typeless=4)
        self.assertEqual(foo.id,qux.id)
        self.assertEqual(qux.typeless, 4)

    def test_find_one(self):
        foo = Foo()
        foo.bar = u'find_one'
        idval = foo.save(safe=True)
        foo2 = Foo.find_one({u'bar':u'find_one'})
        self.assertTrue(foo2._get_id() == idval)
        self.assertTrue(foo2 == foo)

    def test_bad_find_one(self):
        foo = Foo.new(bar = u'bad_find_one')
        foo.save()
        item = foo.find_one()
        self.assertTrue(item)
        item = foo.find_one({}, timeout=False)
        self.assertTrue(item)
        with self.assertRaises(ValueError):
            foo.find_one(bar = u'bad_find_one')

    def test_count(self):
        foo = Foo()
        foo.bar = u'count'
        foo.save(safe=True)
        count = Foo.count()
        self.assertTrue(count == 1)

    def test_grab(self):
        foo = Foo()
        foo.bar = u'grab'
        idval = foo.save(safe=True)
        newfoo = Foo.grab(str(idval))
        self.assertTrue(newfoo != None)
        self.assertTrue(newfoo.id == idval)
        self.assertTrue(newfoo._id == idval)

    def test_find(self):
        foo = Foo()
        foo.bar = u'find'
        foo.save(safe=True)
        foo2 = Foo()
        foo2.bar = u'find'
        foo2.save()
        result = Foo.find({'bar':u'find'})
        self.assertTrue(result.count() == 2)
        f = result[0] # should be first one
        self.assertTrue(type(f) is Foo)
        self.assertTrue(f.bar == u'find')
        for f in result:
            self.assertTrue(type(f) is Foo)

    def test_bad_find(self):
        foo = Foo.new(bar = u'bad_find')
        foo.save(safe=True)
        cursor = foo.find()
        self.assertTrue(cursor.count())
        cursor = foo.find({}, timeout=False)
        self.assertTrue(cursor.count())
        with self.assertRaises(ValueError):
            foo.find(bar = u'bad_find')

    def test_setattr_save(self):
        foo = Foo(bar=u"baz")
        foo.save(safe=True)
        self.assertTrue(Foo.grab(foo.id) != None)
        setattr(foo, "bar", u"quz")
        self.assertEqual(foo.bar, u"quz")
        self.assertEqual(getattr(foo, "bar"), "quz")
        foo.save(safe=True)
        result = Foo.grab(foo.id)
        self.assertEqual(result.bar, "quz")

    def test_save_over(self):
        foo = Foo()
        foo.bar = u'update'
        foo.save(safe=True)
        result = Foo.find_one({'bar':u'update'})
        result["hidden"] = True
        #result.bar = u"new update"
        setattr(result, "bar", u"new update")
        result.save(safe=True)
        result2 = Foo.find_one({'bar': 'new update'})
        self.assertEqual(result.id, result2.id)
        self.assertTrue(result == result2)
        self.assertTrue(result["hidden"])
        self.assertTrue(result2["hidden"])
        self.assertTrue(result2.bar == u'new update')
        self.assertTrue(result.bar == u'new update')


    def test_flexible_fields(self):
        """ Test that anything can be passed in """
        try:
            mogo.AUTO_CREATE_FIELDS = True
            class Flexible(Model):
                pass
            instance = Flexible(foo="bar", age=5)
            instance.save(safe=True)
            self.assertEqual(instance["foo"], "bar")
            self.assertEqual(instance.foo, "bar")
            self.assertEqual(instance["age"], 5)
            self.assertEqual(instance.age, 5)

            retrieved = Flexible.find_one()
            self.assertTrue(retrieved == instance)
            # Test that the flexible fields were set
            self.assertEqual(instance.foo, "bar")
            self.assertEqual(instance.age, 5)
        finally:
            mogo.AUTO_CREATE_FIELDS = False


    def test_class_update(self):
        class Mod(Model):
            val = Field(int)
            mod = Field(int)

        for i in range(100):
            foo = Mod(val=i, mod=i%2)
            foo.save(safe=True)
        Mod.update({"mod": 1}, {"$set": {"mod": 0}}, safe=True)
        self.assertEquals(Mod.search(mod=0).count(), 51)
        Mod.update({"mod": 1}, {"$set": {"mod": 0}}, multi=True, safe=True)
        self.assertEquals(Mod.search(mod=0).count(), 100)

    def test_instance_update(self):
        class Mod(Model):
            val = Field(int)
            mod = Field(int)

        for i in range(100):
            foo = Mod(val=i, mod=i%2)
            foo.save(safe=True)
        foo = Mod.find_one({"mod": 1})
        self.assertRaises(TypeError, foo.update, mod=u"testing", safe=True)
        foo.update(mod=5, safe=True)
        self.assertEquals(foo.mod, 5)
        foo2 = Mod.grab(foo.id)
        self.assertEquals(foo2.mod, 5)
        self.assertEquals(Mod.search(mod=5).count(), 1)

    def test_ref(self):
        foo = Foo()
        foo.bar = u"ref"
        foo.save(safe=True)
        #result = Foo.find_one({"bar": "ref"})
        new = Foo.find_one({"bar": "ref"})
        #new.bar = "Testing"
        new.ref = foo
        new.save(safe=True)
        result2 = Foo.find_one({"bar": "ref"})
        self.assertTrue(result2.ref == foo)

    def test_search(self):
        nothing = Foo.search(bar=u'whatever').first()
        self.assertEqual(nothing, None)
        foo = Foo()
        foo.bar = u"search"
        foo.save(safe=True)
        result = foo.search(bar=u"search")
        self.assertTrue(result.count() == 1)
        self.assertTrue(result.first() == foo)

    def test_search_before_new(self):
        """ Testing the bug where fields are not populated before search. """
        class Bar(Model):
            field = Field()
        result_id = self._conn[DBNAME]["bar"].save({"field": "test"})
        result = Bar.search(field="test").first()
        self.assertEqual(result.id, result_id)


    def test_bad_remove(self):
        foo = Foo()
        foo.bar = u"bad_remove"
        foo.save(safe=True)
        self.assertRaises(TypeError, getattr, args=(foo, 'remove'))

    def test_bad_drop(self):
        foo = Foo()
        foo.bar = u"bad_drop"
        foo.save(safe=True)
        self.assertRaises(TypeError, getattr, args=(foo, "drop"))

    def test_search_ref(self):
        company = Company(name="Foo, Inc.")
        company.save()
        user = Person(name="Test", email="whatever@whatever.com")
        user.company = company
        user.save(safe=True)
        self.assertTrue(company.people.count() == 1)

    def test_group(self):
        db = self._conn[DBNAME]
        for i in range(100):
            obj = {"alt": i % 2, "count": i}
            db.counter.save(obj, safe=True)
        class Counter(Model):
            pass

        result = Counter.group(
            key = { 'alt': 1 },
            condition = { 'alt': 0 },
            reduce = 'function (obj, prev) { prev.count += obj.count; }',
            initial = {'count': 0 }
        )
        self.assertEqual(result[0]['count'], 2450)

    def test_order(self):

        class OrderTest(Model):
            up = Field(int)
            down = Field(int)
            mod = Field(int)

        for i in range(100):
            obj = OrderTest(up=i, down=99-i, mod=i%10)
            obj.save()

        results = []
        query1 = OrderTest.search().order(up=DESC)
        query2 = OrderTest.search().order(mod=DESC).order(up=DESC)
        for obj in query1:
            results.append(obj.up)
            if len(results) == 5:
                break

        self.assertTrue(results == [99, 98, 97, 96, 95])
        mod_result = query2.first()
        self.assertTrue(mod_result.mod == 9)
        self.assertTrue(mod_result.up == 99)

    def test_simple_inheritance(self):
        """ Test simple custom model inheritance """
        person = Person(name="Testing")
        subperson = SubPerson(name="Testing", another_field="foobar")
        person.save(safe=True)
        subperson.save(safe=True)
        self.assertEqual(Person.find().count(), 2)
        # Doesn't automatically return instances of proper type yet
        self.assertEqual(Person.find()[0].name, "Testing")
        self.assertEqual(Person.find()[1]['another_field'], "foobar")

    def test_poly_model_inheritance(self):
        """ Test the mogo support for model inheritance """
        self.assertEqual(Car._get_name(), SportsCar._get_name())
        self.assertEqual(Car._get_collection(), SportsCar._get_collection())
        car = Car()
        with self.assertRaises(NotImplementedError):
            car.drive()
        # FIXME: Split these tests up.
        self.assertEqual(car.doors, 4)
        self.assertEqual(car.wheels, 4)
        self.assertEqual(car.type, "car")
        car.save(safe=True)
        self.assertEqual(Car.find().count(), 1)
        car2 = Car.find().first()
        self.assertEqual(car, car2)
        self.assertEqual(car.copy(), car2.copy())
        self.assertTrue(isinstance(car2, Car))
        sportscar = SportsCar()
        sportscar.save(safe=True)
        self.assertTrue(sportscar.drive())
        self.assertEqual(sportscar.doors, 2)
        self.assertEqual(sportscar.wheels, 4)
        self.assertEqual(sportscar.type, "sportscar")
        self.assertEqual(SportsCar.find().count(), 1)
        sportscar = SportsCar.find().first()
        self.assertEqual(sportscar.doors, 2)
        self.assertEqual(sportscar.type, "sportscar")
        self.assertEqual(Car.find().count(), 2)
        sportscar2 = Car.find({"doors":2}).first()
        self.assertTrue(isinstance(sportscar2, SportsCar))
        self.assertTrue(sportscar2.drive())
        convertible = Car(type=u"convertible")
        convertible.save(safe=True)
        self.assertEqual(convertible.doors, 2)
        self.assertTrue(convertible.toggle_roof())
        self.assertFalse(convertible.toggle_roof())

        all_cars = list(Car.find())
        self.assertEqual(len(all_cars), 3)
        car, sportscar, convertible = all_cars
        self.assertTrue(isinstance(car, Car))
        self.assertTrue(isinstance(sportscar, SportsCar))
        self.assertTrue(isinstance(convertible, Convertible))

        self.assertEqual(SportsCar.search().count(), 1)

        self.assertEqual(Convertible.find_one(), convertible)

    def test_representation_methods(self):
        """ Test __repr__, __str__, and __unicode__ """
        repr_result = Foo().__repr__()
        str_result = Foo().__str__()
        unicode_result = Foo().__unicode__()
        hypo = "FOOBAR"
        self.assertTrue(repr_result == str_result == unicode_result == hypo)

    def test_session(self):
        """ Test using a session on a model """
        foo = Foo()
        foo.save(safe=True)
        self.assertEqual(Foo.find().count(), 1)
        session = mogo.session(ALTDB)
        session.connect()
        FooWrapped = Foo.use(session)
        self.assertEqual(FooWrapped._get_name(), Foo._get_name())
        self.assertEqual(FooWrapped.find().count(), 0)
        coll = session.connection.get_collection("foo")
        self.assertEqual(coll.find().count(), 0)
        foo2 = FooWrapped()
        foo2.save(safe=True)
        self.assertEqual(coll.find().count(), 1)
        session.disconnect()

    def test_connection_with_statement(self):
        """ Test the with statement alternate connection """
        with mogo.session(ALTDB) as s:
            foo = Foo.use(s)(bar=u"testing_with_statement")
            foo.save(safe=True)
            results = Foo.use(s).find({"bar": "testing_with_statement"})
            self.assertEqual(results.count(), 1)
            result = results.first()
            self.assertEqual(result, foo)
        count = Foo.find().count()
        self.assertEqual(count, 0)

    def test_constant_field(self):
        """ Test the ConstantField """
        class ConstantModel(Model):
            name = Field(unicode, required=True)
            constant = ConstantField(int, required=True)

        # this is fine
        model = ConstantModel(name=u"whatever", constant=10)
        self.assertEqual(10, model.constant)
        # as is this
        model.constant = 5
        model.save(safe=True)
        self.assertEqual(5, model.constant)

        # this is also okay (since it's the same value)
        model.constant = 5
        self.assertEqual(5, model.constant)
        # but this is not allowed
        def set_constant():
            model.constant = 10

        self.assertRaises(ValueError, set_constant)
        self.assertEqual(5, model.constant)

    def test_custom_callbacks(self):
        """ Test the various set and get callback options. """
        class CustomField(Field):

            def _get_callback(self, instance, value):
                return 5

            def _set_callback(self, instance, value):
                return 8

        def custom_get(instance, value):
            return 1

        def custom_set(instance, value):
            return 2

        class CustomModel(Model):
            custom1 = Field(get_callback=custom_get, set_callback=custom_set)
            custom2 = CustomField()
            custom3 = CustomField(get_callback=custom_get,
                set_callback=custom_set)

        custom_model = CustomModel()
        self.assertEqual(1, custom_model.custom1)
        custom_model.custom1 = 15
        self.assertEqual(2, custom_model["custom1"])
        self.assertEqual(5, custom_model.custom2)
        custom_model.custom2 = 15
        self.assertEqual(8, custom_model["custom2"])
        self.assertEqual(1, custom_model.custom3)
        custom_model.custom3 = 15
        self.assertEqual(2, custom_model["custom3"])

    def test_first(self):
        foo = Foo()
        foo.bar = u"search"
        foo.save(safe=True)
        for x in xrange(3):
            foo_x = Foo()
            foo_x.bar = u"search"
            foo_x.save(safe=True)
        result = foo.first(bar=u"search")
        self.assertTrue(result == foo)

    def tearDown(self):
        if DELETE:
            self._conn.drop_database(DBNAME)
            self._conn.drop_database(ALTDB)
        self._conn.disconnect()

if __name__ == '__main__':
    if '--no-drop' in sys.argv:
        DELETE = False
        sys.argv.remove('--no-drop')
    unittest.main()
