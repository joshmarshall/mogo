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
from mogo import Model, connect, Field, ReferenceField, DESC
from mogo.connection import Connection
import pymongo
import pymongo.objectid
import sys
from datetime import datetime

DBNAME = '_mogotest'
DELETE = True

class Foo(Model):
    bar = Field(unicode)
    typeless = Field()
    dflt = Field(unicode, default=u'dflt')
    callme = Field(unicode, default=lambda: u'funtimes')
    dtnow = Field(datetime, default=lambda: datetime.now())

Foo.ref = ReferenceField(Foo)

class Company(Model):
    name = Field(str)

    @property
    def people(self):
        return Person.search(company=self)

class Person(Model):
    company = ReferenceField(Company)
    name = Field(str)
    email = Field(str)


class MogoTests(unittest.TestCase):

    def test_connect(self):
        conn = connect(DBNAME)
        self.assertTrue(isinstance(conn, pymongo.Connection))
        connection = Connection.instance()
        self.assertTrue(connection._database == DBNAME)
        conn.disconnect()

    def test_model(self):
        foo = Foo.new(bar=u'cheese')
        self.assertTrue(foo.bar == u'cheese')
        self.assertTrue(foo.dflt == u'dflt')
        self.assertTrue(foo.callme == u'funtimes')
        self.assertTrue(isinstance(foo.dtnow, datetime))
        foo.bar = u'model'
        self.assertTrue(foo.bar == u'model')

    def test_save_defaults(self):
        """
        test that default values get saved alongside other values when creating
        the model.
        """
        foo = Foo.new(bar=u'goat')
        id_ = foo.save(safe=True)
        raw_result = Foo._collection.find_one({"_id": id_})
        self.assertTrue(raw_result["dflt"] == u'dflt')

    def test_create_delete(self):
        conn = connect(DBNAME)
        foo = Foo.new()
        foo.bar = u'create_delete'
        idval = foo.save(safe=True)
        try:
            self.assertTrue(type(idval) is pymongo.objectid.ObjectId)
            self.assertTrue(foo.id == idval)
        finally:
            foo.delete()
            conn.disconnect()

    def test_find_one(self):
        conn = connect(DBNAME)
        foo = Foo.new()
        foo.bar = u'find_one'
        idval = foo.save(safe=True)
        foo2 = Foo.find_one({u'bar':u'find_one'})
        try:
            self.assertTrue(foo2._get_id() == idval)
            self.assertTrue(foo2 == foo)
        finally:
            foo.delete()
            conn.disconnect()

    def test_count(self):
        conn = connect(DBNAME)
        foo = Foo.new()
        foo.bar = u'count'
        foo.save(safe=True)
        count = Foo.count()
        try:
            self.assertTrue(count == 1)
        finally:
            foo.delete()
            conn.disconnect()

    def test_grab(self):
        conn = connect(DBNAME)
        foo = Foo.new()
        foo.bar = u'grab'
        idval = foo.save(safe=True)
        newfoo = Foo.grab(str(idval))
        try:
            self.assertTrue(newfoo != None)
            self.assertTrue(newfoo.id == idval)
        finally:
            foo.delete()
            conn.disconnect()

    def test_find(self):
        conn = connect(DBNAME)
        foo = Foo.new()
        foo.bar = u'find'
        foo.save(safe=True)
        foo2 = Foo.new()
        foo2.bar = u'find'
        foo2.save()
        result = Foo.find({'bar':u'find'})
        self.assertTrue(result.count() == 2)
        f = result[0] # should be first one
        try:
            self.assertTrue(type(f) is Foo)
            self.assertTrue(f.bar == u'find')
            for f in result:
                self.assertTrue(type(f) is Foo)
        finally:
            foo.delete()
            foo2.delete()
            conn.disconnect()

    def test_save_over(self):
        conn = connect(DBNAME)
        foo = Foo.new()
        foo.bar = u'update'
        foo.save(safe=True)
        result = Foo.find_one({'bar':u'update'})
        result.bar = u"new update"
        result["hidden"] = True
        result.save(safe=True)
        result2 = Foo.find_one({'bar': 'new update'})
        try:
            self.assertTrue(result == result2)
            self.assertTrue(result["hidden"])
            self.assertTrue(result2["hidden"])
            self.assertTrue(result2.bar == u'new update')
            self.assertTrue(result.bar == u'new update')
        finally:
            foo.delete()
            conn.disconnect()

    def test_class_update(self):
        class Mod(Model):
            val = Field(int)
            mod = Field(int)

        for i in range(100):
            foo = Mod.new(val=i, mod=i%2)
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
            foo = Mod.new(val=i, mod=i%2)
            foo.save(safe=True)
        foo = Mod.find_one({"mod": 1})
        self.assertRaises(TypeError, foo.update, mod=u"testing", safe=True)
        foo.update(mod=5, safe=True)
        self.assertEquals(foo.mod, 5)
        foo2 = Mod.grab(foo.id)
        self.assertEquals(foo2.mod, 5)
        self.assertEquals(Mod.search(mod=5).count(), 1)

    def test_ref(self):
        conn = connect(DBNAME)
        foo = Foo.new()
        foo.bar = u"ref"
        foo.save(safe=True)
        #result = Foo.find_one({"bar": "ref"})
        new = Foo.find_one({"bar": "ref"})
        #new.bar = "Testing"
        new.ref = foo
        new.save(safe=True)
        result2 = Foo.find_one({"bar": "ref"})
        try:
            self.assertTrue(result2.ref == foo)
        finally:
            result2.delete()
            conn.disconnect()

    def test_search(self):
        conn = connect(DBNAME)
        foo = Foo.new()
        foo.bar = u"search"
        foo.save(safe=True)
        result = foo.search(bar=u"search")
        try:
            self.assertTrue(result.count() == 1)
            self.assertTrue(result.first() == foo)
        finally:
            foo.delete()
            conn.disconnect()

    def test_bad_remove(self):
        conn = connect(DBNAME)
        foo = Foo.new()
        foo.bar = u"bad_remove"
        foo.save(safe=True)
        try:
            self.assertRaises(TypeError, getattr, args=(foo, 'remove'))
        finally:
            foo.delete()
            conn.disconnect()

    def test_bad_drop(self):
        conn = connect(DBNAME)
        foo = Foo.new()
        foo.bar = u"bad_drop"
        foo.save(safe=True)
        try:
            self.assertRaises(TypeError, getattr, args=(foo, "drop"))
        finally:
            foo.delete()
            conn.disconnect()

    def test_search_ref(self):
        conn = connect(DBNAME)
        company = Company.new(name="Foo, Inc.")
        company.save()
        user = Person.new(name="Test", email="whatever@whatever.com")
        user.company = company
        user.save(safe=True)
        try:
            self.assertTrue(company.people.count() == 1)
        finally:
            user.delete()
            company.delete()
            conn.disconnect()

    def test_group(self):
        conn = pymongo.Connection()
        db = conn[DBNAME]
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
            obj = OrderTest.new(up=i, down=99-i, mod=i%10)
            obj.save()

        results = []
        query1 = OrderTest.search().order(up=DESC)
        query2 = OrderTest.search().order(mod=DESC).order(up=DESC)
        for obj in query1:
            results.append(obj.up)
            if len(results) == 5:
                break

        try:
            self.assertTrue(results == [99, 98, 97, 96, 95])
            mod_result = query2.first()
            self.assertTrue(mod_result.mod == 9)
            self.assertTrue(mod_result.up == 99)
        finally:
            OrderTest.remove()
            OrderTest.drop()


    def tearDown(self):
        conn = pymongo.Connection()
        if DELETE:
            conn.drop_database(DBNAME)

if __name__ == '__main__':
    if '--no-drop' in sys.argv:
        DELETE = False
        sys.argv.remove('--no-drop')
    unittest.main()
