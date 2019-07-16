"""
NOTES:
You need to have mongod running on the local machine for this
to run. Will probably add config options later for testing
remote machines.

If for some reason you have a database named "_mogotest", you will
probably want to change DBNAME. :)
"""

from datetime import datetime
import unittest
import warnings

from bson.objectid import ObjectId
import mogo
from mogo import PolyModel, Model, Field, ReferenceField, DESC, connect
from mogo import ConstantField
from mogo.connection import Connection
from mogo.cursor import Cursor
from mogo.model import UnknownField
import pymongo

from typing import Any, cast, Optional, Type, TypeVar


T = TypeVar("T")


DBNAME = '_mogotest'
ALTDB = "_mogotest2"
DELETE = True


class Foo(Model):
    bar = Field(str)
    typeless = Field[Any]()
    dflt = Field(str, default=u'dflt')
    callme = Field(str, default=lambda: u'funtimes')
    dtnow = Field(datetime, default=lambda: datetime.now())

    def __unicode__(self) -> str:
        return "FOOBAR"


Foo.ref = ReferenceField(Foo)


F = TypeVar("F", bound="FooWithNew")


class FooWithNew(Model):
    bar = Field(str)

    @classmethod
    def new(cls: Type[F], **kwargs: Any) -> F:
        return cls(bar="whatever")


class Company(Model):
    name = Field[str](str)

    @property
    def people(self) -> Cursor["Person"]:
        return Person.search(company=self)


class Person(Model):
    _name = "people"
    company = ReferenceField(Company)
    name = Field[str](str)
    email = Field[str](str)


class SubPerson(Person):
    """ Testing inheritance """
    another_field = Field[str](str)


class Car(PolyModel):
    """ Base model for alternate inheritance """
    doors = Field[int](int, default=4)
    wheels = Field[int](int, default=4)
    type = Field[str](str, default="car")

    @classmethod
    def get_child_key(cls) -> str:
        return "type"

    def drive(self) -> bool:
        """ Example method to overwrite """
        raise NotImplementedError("Implement this in child classes")


@Car.register("sportscar")
class SportsCar(Car):
    """ Alternate car """
    doors = Field[int](int, default=2)
    type = Field[str](str, default="sportscar")

    def drive(self) -> bool:
        """ Overwritten """
        return True


@Car.register
class Convertible(SportsCar):
    """ New methods """

    _top_down = False  # type: bool

    type = Field[str](str, default="convertible")

    def toggle_roof(self) -> bool:
        """ Opens / closes roof """
        self._top_down = not self._top_down
        return self._top_down


class TestMogoGeneralUsage(unittest.TestCase):

    def setUp(self) -> None:
        self._conn = connect(DBNAME)

    def assert_not_none(self, obj: Optional[T]) -> T:
        # this is just a custom version of assertIsNotNone that
        # returns the object of the correct type if it's not null
        if obj is None:
            self.fail("Object unexpectedly none.")
        return obj

    def test_connect(self) -> None:
        self.assertRaises(ValueError, connect)
        self.assertIsInstance(self._conn, pymongo.MongoClient)
        connection = Connection.instance()
        self.assertEqual(connection._database, DBNAME)
        self._conn.close()

    def test_uri_connect(self) -> None:
        conn = connect(uri="mongodb://localhost/%s" % DBNAME)
        self.assertIsInstance(conn, pymongo.MongoClient)
        connection = Connection.instance()
        self.assertEqual(connection._database, DBNAME)
        conn.close()
        # overriding the database name
        conn = connect(DBNAME, uri="mongodb://localhost/foobar")
        self.assertIsInstance(conn, pymongo.MongoClient)
        connection = Connection.instance()
        self.assertEqual(connection._database, DBNAME)
        conn.close()

    def test_model(self) -> None:
        foo = Foo(bar=u'cheese')
        self.assertEqual(foo.bar, u'cheese')
        self.assertEqual(foo.dflt, u'dflt')
        self.assertEqual(foo.callme, u'funtimes')
        self.assertIsInstance(foo.dtnow, datetime)
        foo.bar = u'model'
        self.assertEqual(foo.bar, u'model')

    def test_model_create(self) -> None:
        foo = Foo.create(bar="cheese")
        self.assertEqual(foo.bar, "cheese")
        self.assertEqual(Foo.find().count(), 1)
        # testing with a classmethod "new" defined.
        foo2 = FooWithNew.create()
        self.assertIsNotNone(foo2._id)
        self.assertEqual(foo2.bar, "whatever")

    def test_save_defaults(self) -> None:
        """
        test that default values get saved alongside other values when creating
        the model.
        """
        foo = Foo(bar=u'goat')
        id_ = foo.save(w=1)
        raw_result = self.assert_not_none(
            Foo._get_collection().find_one({"_id": id_}))
        self.assertEqual(raw_result["dflt"], u'dflt')

    def test_create_delete(self) -> None:
        foo = Foo()
        foo.bar = u'create_delete'
        idval = foo.save()
        self.assertIs(type(idval), ObjectId)
        self.assertEqual(foo.id, idval)

    def test_search_or_create(self) -> None:
        foo = Foo.search_or_create(bar=u'howdy')
        self.assertIsInstance(foo._id, ObjectId)
        foo.typeless = 4
        foo.save()

        baz = Foo.search_or_create(bar=u'howdy', typeless=2)
        self.assertNotEqual(foo.id, baz.id)
        self.assertEqual(baz.typeless, 2)

        qux = Foo.search_or_create(bar=u'howdy', typeless=4)
        self.assertEqual(foo.id, qux.id)
        self.assertEqual(qux.typeless, 4)

    def test_find_one(self) -> None:
        foo = Foo()
        foo.bar = u'find_one'
        idval = foo.save()
        foo2 = self.assert_not_none(Foo.find_one({u'bar': u'find_one'}))
        self.assertEqual(foo2._get_id(), idval)
        self.assertEqual(foo2, foo)

    def test_bad_find_one(self) -> None:
        foo = Foo.new(bar=u'bad_find_one')
        foo.save()
        item = foo.find_one()
        self.assertTrue(item)
        item = foo.find_one({})
        self.assertTrue(item)
        with self.assertRaises(ValueError):
            foo.find_one(bar=u'bad_find_one')

    def test_bad_remove_arguments(self) -> None:
        foo = Foo.create(bar="testing")
        foo.save()
        with self.assertRaises(ValueError):
            Foo.remove(bar="testing")
        with self.assertRaises(ValueError):
            Foo.remove()
        self.assertEqual(Foo.count(), 1)

    def test_count(self) -> None:
        foo = Foo()
        foo.bar = u'count'
        foo.save()
        count = Foo.count()
        self.assertEqual(count, 1)

    def test_grab(self) -> None:
        foo = Foo()
        foo.bar = u'grab'
        idval = foo.save()
        newfoo = self.assert_not_none(Foo.grab(str(idval)))
        self.assertEqual(newfoo.id, idval)
        self.assertEqual(newfoo._id, idval)

    def test_find(self) -> None:
        foo = Foo()
        foo.bar = u'find'
        foo.save()
        foo2 = Foo()
        foo2.bar = u'find'
        foo2.save()
        result = Foo.find({'bar': u'find'})
        self.assertEqual(result.count(), 2)
        f = result[0]  # should be first one
        self.assertIs(type(f), Foo)
        self.assertEqual(f.bar, u'find')
        for f in result:
            self.assertIs(type(f), Foo)

    def test_find_next_fallback(self) -> None:
        # this is mostly to verify Python 3 compatibility with the next()
        foo = Foo.create(bar="find")
        foo2 = Foo.create(bar="find")
        result = Foo.find({'bar': u'find'})
        self.assertEqual(foo, result.next())
        self.assertEqual(foo2, result.next())
        with self.assertRaises(StopIteration):
            result.next()

    def test_find_len(self) -> None:
        foo = Foo(bar=u'find')
        foo.save()
        foo2 = Foo(bar=u'find')
        foo2.save()
        result = Foo.find({'bar': u'find'})
        self.assertEqual(result.count(), 2)
        self.assertEqual(len(result), 2)

    def test_bad_find(self) -> None:
        foo = Foo.new(bar=u'bad_find')
        foo.save()
        cursor = foo.find()
        self.assertTrue(cursor.count())
        cursor = foo.find({})
        self.assertTrue(cursor.count())
        with self.assertRaises(ValueError):
            foo.find(bar=u'bad_find')

    def test_setattr_save(self) -> None:
        foo = Foo(bar="baz")
        foo.save()
        self.assertIsNotNone(Foo.grab(foo.id))
        setattr(foo, "bar", "quz")
        self.assertEqual(foo.bar, "quz")
        self.assertEqual(getattr(foo, "bar"), "quz")
        foo.save()
        result = self.assert_not_none(Foo.grab(foo.id))
        self.assertEqual(result.bar, "quz")

    def test_save_over(self) -> None:
        foo = Foo()
        foo.bar = u'update'
        foo.save()
        result = self.assert_not_none(Foo.find_one({'bar': u'update'}))
        result["hidden"] = True
        setattr(result, "bar", "new update")
        result.save()
        result2 = self.assert_not_none(Foo.find_one({'bar': 'new update'}))
        self.assertEqual(result.id, result2.id)
        self.assertEqual(result, result2)
        self.assertTrue(result["hidden"])
        self.assertTrue(result2["hidden"])
        self.assertEqual(result2.bar, u'new update')
        self.assertEqual(result.bar, u'new update')

    def test_flexible_fields(self) -> None:
        """ Test that anything can be passed in """
        try:
            mogo.AUTO_CREATE_FIELDS = True

            class Flexible(Model):
                pass
            instance = Flexible(foo="bar", age=5)
            instance.save()
            self.assertEqual(instance["foo"], "bar")
            self.assertEqual(instance.foo, "bar")  # type: ignore
            self.assertEqual(instance["age"], 5)
            self.assertEqual(instance.age, 5)  # type: ignore

            retrieved = self.assert_not_none(Flexible.find_one())
            self.assertEqual(retrieved, instance)
            # Test that the flexible fields were set
            self.assertEqual(instance.foo, "bar")  # type: ignore
            self.assertEqual(instance.age, 5)  # type: ignore
        finally:
            mogo.AUTO_CREATE_FIELDS = False

    def test_flexible_fields_model_overwrite(self) -> None:
        """ Overwrite on a per-model basis """
        class Flexible(Model):
            AUTO_CREATE_FIELDS = True

        instance = Flexible.create(foo="bar", age=5)
        self.assertEqual("bar", instance.foo)  # type: ignore
        self.assertEqual(5, instance.age)  # type: ignore

    def test_flexible_fields_model_overwrites_global(self) -> None:
        try:
            mogo.AUTO_CREATE_FIELDS = True

            class Flexible(Model):
                AUTO_CREATE_FIELDS = False

            with self.assertRaises(UnknownField):
                Flexible.create(foo="bar", age=5)
        finally:
            mogo.AUTO_CREATE_FIELDS = False

    def test_class_update(self) -> None:
        class Mod(Model):
            val = Field(int)
            mod = Field(int)

        for i in range(100):
            foo = Mod(val=i, mod=i % 2)
            foo.save()
        Mod.update({"mod": 1}, {"$set": {"mod": 0}})
        self.assertEqual(Mod.search(mod=0).count(), 51)
        Mod.update(
            {"mod": 1}, {"$set": {"mod": 0}}, multi=True)
        self.assertEqual(Mod.search(mod=0).count(), 100)

    def test_instance_update(self) -> None:
        class Mod(Model):
            val = Field(int)
            mod = Field(int)

        for i in range(100):
            foo = Mod(val=i, mod=i % 2)
            foo.save()
        foo = self.assert_not_none(Mod.find_one({"mod": 1}))
        with self.assertRaises(TypeError):
            foo.update(mod="testing")
        foo.update(mod=5)
        self.assertEqual(foo.mod, 5)
        foo2 = self.assert_not_none(Mod.grab(foo.id))
        self.assertEqual(foo2.mod, 5)
        self.assertEqual(Mod.search(mod=5).count(), 1)

    def test_cursor_update(self) -> None:
        class Atomic(Model):
            value = Field(int)
            key = Field(str, default="foo")
            unchanged = Field(default="original")

        for i in range(10):
            atomic = Atomic(value=i)
            if i % 2:
                atomic.key = "bar"
            atomic.save()

        Atomic.find({"key": "bar"}).update({"$inc": {"value": 100}})
        Atomic.find({"key": "foo"}).change(key="wut")

        self.assertEqual(5, Atomic.find({"key": "wut"}).count())
        self.assertEqual(5, Atomic.find({"value": {"$gt": 100}}).count())
        self.assertEqual(10, Atomic.find({"unchanged": "original"}).count())

    def test_ref(self) -> None:
        foo = Foo()
        foo.bar = "ref"
        foo.save()
        new = self.assert_not_none(Foo.find_one({"bar": "ref"}))
        new.ref = foo  # type: ignore
        new.save()
        result2 = self.assert_not_none(Foo.find_one({"bar": "ref"}))
        self.assertEqual(result2.ref, foo)  # type: ignore

    def test_search(self) -> None:
        nothing = Foo.search(bar=u'whatever').first()
        self.assertEqual(nothing, None)
        foo = Foo()
        foo.bar = "search"
        foo.save()
        result = foo.search(bar="search")
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), foo)

    def test_search_before_new(self) -> None:
        """ Testing the bug where fields are not populated before search. """
        class Bar(Model):
            field = Field[Any]()
        insert_result = self._conn[DBNAME]["bar"].insert_one({"field": "test"})
        result_id = insert_result.inserted_id
        result = self.assert_not_none(Bar.search(field="test").first())
        self.assertEqual(result.id, result_id)

    def test_bad_remove(self) -> None:
        foo = Foo()
        foo.bar = "bad_remove"
        foo.save()
        self.assertRaises(TypeError, getattr, args=(foo, 'remove'))

    def test_bad_drop(self) -> None:
        foo = Foo()
        foo.bar = "bad_drop"
        foo.save()
        self.assertRaises(TypeError, getattr, args=(foo, "drop"))

    def test_search_ref(self) -> None:
        company = Company(name="Foo, Inc.")
        company.save()
        user = Person(name="Test", email="whatever@whatever.com")
        user.company = company
        user.save()
        self.assertEqual(company.people.count(), 1)

    def test_group(self) -> None:
        db = self._conn[DBNAME]
        for i in range(100):
            obj = {"alt": i % 2, "count": i}
            db["counter"].insert_one(obj)

        class Counter(Model):
            pass

        with warnings.catch_warnings(record=True) as warn_entries:
            warnings.simplefilter("always")
            result = Counter.group(
                key={'alt': 1},
                condition={'alt': 0},
                reduce='function (obj, prev) { prev.count += obj.count; }',
                initial={'count': 0})
            entries = self.assert_not_none(warn_entries)
            self.assertEqual(1, len(entries))
            self.assertTrue(
                issubclass(entries[0].category, DeprecationWarning))
        self.assertEqual(result[0]['count'], 2450)  # type: ignore

    def test_order(self) -> None:

        class OrderTest(Model):
            up = Field(int)
            down = Field(int)
            mod = Field(int)

        for i in range(100):
            obj = OrderTest(up=i, down=99 - i, mod=i % 10)
            obj.save()

        results = []
        query1 = OrderTest.search().order(up=DESC)
        query2 = OrderTest.search().order(mod=DESC).order(up=DESC)
        for obj in query1:
            results.append(obj.up)
            if len(results) == 5:
                break

        self.assertEqual(results, [99, 98, 97, 96, 95])
        mod_result = self.assert_not_none(query2.first())
        self.assertEqual(mod_result.mod, 9)
        self.assertEqual(mod_result.up, 99)

    def test_simple_inheritance(self) -> None:
        """ Test simple custom model inheritance """
        person = Person(name="Testing")
        subperson = SubPerson(name="Testing", another_field="foobar")
        person.save()
        subperson.save()
        self.assertEqual(Person.find().count(), 2)
        # Doesn't automatically return instances of proper type yet
        self.assertEqual(Person.find()[0].name, "Testing")
        self.assertEqual(Person.find()[1]['another_field'], "foobar")

    def test_poly_model_inheritance(self) -> None:
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
        car.save()
        self.assertEqual(Car.find().count(), 1)
        car2 = self.assert_not_none(Car.find().first())
        self.assertEqual(car, car2)
        self.assertEqual(car.copy(), car2.copy())
        self.assertIsInstance(car2, Car)
        sportscar = SportsCar()
        sportscar.save()
        self.assertTrue(sportscar.drive())
        self.assertEqual(sportscar.doors, 2)
        self.assertEqual(sportscar.wheels, 4)
        self.assertEqual(sportscar.type, "sportscar")
        self.assertEqual(SportsCar.find().count(), 1)
        sportscar2 = self.assert_not_none(SportsCar.find().first())
        self.assertEqual(sportscar2.doors, 2)
        self.assertEqual(sportscar2.type, "sportscar")
        self.assertEqual(Car.find().count(), 2)
        sportscar3 = self.assert_not_none(Car.find({"doors": 2}).first())
        self.assertIsInstance(sportscar3, SportsCar)
        self.assertTrue(sportscar3.drive())
        convertible = cast(Convertible, Car(type="convertible"))
        convertible.save()
        self.assertEqual(convertible.doors, 2)
        self.assertTrue(convertible.toggle_roof())
        self.assertFalse(convertible.toggle_roof())

        all_cars = list(Car.find())
        self.assertEqual(len(all_cars), 3)
        self.assertIsInstance(all_cars[0], Car)
        self.assertIsInstance(all_cars[1], SportsCar)
        self.assertIsInstance(all_cars[2], Convertible)

        self.assertEqual(SportsCar.search().count(), 1)

        self.assertEqual(Convertible.find_one(), convertible)

    def test_representation_methods(self) -> None:
        """ Test __repr__, __str__, and __unicode__ """
        repr_result = repr(Foo())
        str_result = Foo().__str__()
        str_fn_result = str(Foo())
        hypo = "FOOBAR"
        self.assertTrue(repr_result == str_result == str_fn_result == hypo)

    def test_session(self) -> None:
        """ Test using a session on a model """
        foo = Foo()
        foo.save()
        self.assertEqual(Foo.find().count(), 1)
        session = mogo.session(ALTDB)
        session.connect()
        FooWrapped = Foo.use(session)
        self.assertEqual(FooWrapped._get_name(), Foo._get_name())
        self.assertEqual(FooWrapped.find().count(), 0)
        coll = cast(Connection, session.connection).get_collection("foo")
        self.assertEqual(coll.count_documents({}), 0)
        foo2 = FooWrapped()
        foo2.save()
        self.assertEqual(coll.count_documents({}), 1)
        session.close()

    def test_connection_with_statement(self) -> None:
        """ Test the with statement alternate connection """
        with mogo.session(ALTDB) as s:
            foo = Foo.use(s)(bar="testing_with_statement")
            foo.save()
            results = Foo.use(s).find({"bar": "testing_with_statement"})
            self.assertEqual(results.count(), 1)
            result = results.first()
            self.assertEqual(result, foo)
        count = Foo.find().count()
        self.assertEqual(count, 0)

    def test_constant_field(self) -> None:
        """ Test the ConstantField """
        class ConstantModel(Model):
            name = Field(str, required=True)
            constant = ConstantField(int, required=True)

        # this is fine
        model = ConstantModel(name="whatever", constant=10)
        self.assertEqual(10, model.constant)
        # as is this
        model.constant = 5
        model.save()
        self.assertEqual(5, model.constant)

        # this is also okay (since it's the same value)
        model.constant = 5
        self.assertEqual(5, model.constant)
        # but this is not allowed

        def set_constant() -> None:
            model.constant = 10

        self.assertRaises(ValueError, set_constant)
        self.assertEqual(5, model.constant)

    def test_custom_callbacks(self) -> None:
        """ Test the various set and get callback options. """
        class CustomField(Field[int]):

            def _get_callback(self, instance: Model, value: Any) -> int:
                return 5

            def _set_callback(self, instance: Model, value: Any) -> int:
                return 8

        def custom_get(instance: Model, value: Any) -> int:
            return 1

        def custom_set(instance: Model, value: Any) -> int:
            return 2

        class CustomModel(Model):
            custom1 = Field(get_callback=custom_get, set_callback=custom_set)
            custom2 = CustomField()
            custom3 = CustomField(
                get_callback=custom_get, set_callback=custom_set)

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

    def test_first(self) -> None:
        foo = Foo()
        foo.bar = "search"
        foo.save()
        for x in range(3):
            foo_x = Foo()
            foo_x.bar = "search"
            foo_x.save()
        result = foo.first(bar="search")
        self.assertEqual(result, foo)

    def tearDown(self) -> None:
        if DELETE:
            self._conn.drop_database(DBNAME)
            self._conn.drop_database(ALTDB)
        self._conn.close()
