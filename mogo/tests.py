import unittest
from mogo import Model, connect
from mogo.connection import Connection
import pymongo
import pymongo.objectid
import time

DBNAME = 'mogotest'
MONGOENGINE = False
try:
    import mongoengine as MONGOENGINE
except ImportError:
    pass

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
        
def time_diff():
    conn = connect(DBNAME)
    pydb = conn[DBNAME]
    
    # Setting up the collections (these should be the same time)
    pydb.drop_collection('pyfoo')
    pydb.drop_collection('foo')
    pydb.create_collection('pyfoo')
    pydb.create_collection('foo')
    
    pycoll = pydb['pyfoo']
    mocoll = pydb['foo']
    n = 1000
    pystart = time.time()
    for i in range(n):
        entry = {'bar':'cheese'}
        pyid = pycoll.save(entry)
    result = pycoll.find({'bar':'cheese'})
    for r in result:
        pycoll.remove({'_id':r['_id']})
    pyend = time.time()
    mogostart = time.time()
    for i in range(n):
        foo = Foo(bar='cheese')
        idval = foo.save()
    result = Foo.find({'bar':'cheese'})
    for r in result:
        r.remove()
    mogoend = time.time()
    mogotime = mogoend - mogostart
    pytime = pyend - pystart
    print 'PyMongo for %s inserts / deletes' % n
    print round(pytime, 4)
    print 'Mogo for %s inserts / deletes:' % n
    print round(mogotime, 4)
    if MONGOENGINE:
        me_conn = MONGOENGINE.connect(DBNAME)
        class MEFoo(MONGOENGINE.Document):
            bar = MONGOENGINE.StringField(default='cheese')
        mestart = time.time()
        for i in range(n):
            foo = MEFoo(bar='cheese')
            foo.save()
        result = MEFoo.objects(bar='cheese')
        for r in result:
            r.delete()
        meend = time.time()
        metime = meend - mestart
        print 'MongoEngine for %s inserts / deletes:' % n
        print round(metime, 4)
    print
    
        
if __name__ == '__main__':
    time_diff()
    unittest.main()