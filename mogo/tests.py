import unittest
from mogo import Model, connect
from mogo.connection import Connection
import pymongo
import pymongo.objectid
import time
import hashlib

DBNAME = 'mogotest'

class Foo(Model):
    pass

class UnitTests(unittest.TestCase):
        
    def test_connect(self):
        conn = connect(DBNAME)
        self.assertTrue(isinstance(conn, pymongo.Connection))
        connection = Connection.instance()
        self.assertTrue(Connection.instance()._database == 'mogotest')
        conn.disconnect()
        
    def test_model(self):
        foo = Foo(bar='cheese')
        self.assertTrue(foo.bar == 'cheese')
        foo.bar = 'table'
        self.assertTrue(foo.bar == 'table')
        
    def test_create_delete(self):
        conn = connect(DBNAME)
        foo = Foo()
        foo.bar = 'table'
        idval = foo.save()
        try:
            self.assertTrue(type(idval) is pymongo.objectid.ObjectId)
            self.assertTrue(foo.id == idval)
        finally:
            foo.remove()
            conn.disconnect()
        
    def test_find_one(self):
        conn = connect(DBNAME)
        foo = Foo()
        foo.bar = 'table'
        idval = foo.save()
        foo2 = Foo.find_one({'bar':'table'})
        try:
            self.assertTrue(foo2._get_id() == idval)
            self.assertTrue(foo2 == foo)
        finally:
            foo.remove()
            conn.disconnect()
            
    def test_count(self):
        conn = connect(DBNAME)
        foo = Foo()
        foo.bar = 'table'
        idval = foo.save()
        count = Foo.count()
        self.assertTrue(count == 1)
        foo.remove()
        conn.disconnect()
        
    def test_find(self):
        conn = connect(DBNAME)
        foo = Foo()
        foo.bar = 'table'
        foo.save()
        result = Foo.find({'bar':'table'})
        self.assertTrue(result.count() == 1)
        f = result[0]
        self.assertTrue(type(f) is Foo)
        self.assertTrue(f.bar == 'table')
        for f in result:
            self.assertTrue(type(f) is Foo)
        foo.remove()
        conn.disconnect()
    
    def tearDown(self):
        conn = pymongo.Connection()
        db = conn[DBNAME]
        coll = db['foo']
        coll.remove()
        
if __name__ == '__main__':
    unittest.main()