Mogo 
====
This library is a simple "schema-less" object wrapper around the 
pymongo library (http://github.com/mongodb/mongo-python-driver). Mogo 
is not a full-featured ORM like MongoEngine -- it simply provides some
syntactic sugar so that you can access any PyMongo result with
dot-attribute syntax, as well as attach custom methods to the models.

This emerged from my experience with PyMongo and MongoEngine -- 
while pymongo is very simple to use and really flexible, it doesn't
fully meet the MVC pattern because you are working with plain dicts 
and can't attach model logic anywhere.

MongoEngine, on the other hand, is a heavier implementation on
top of PyMongo, with Django-like syntax. While I liked MongoEngine,
ultimately I wanted the schema-less flexibility of a dict with as 
little between my code and the database as possible.

Mogo is licensed under the Apache License, Version 2.0
(http://www.apache.org/licenses/LICENSE-2.0.html).

Features
--------
* Object oriented design for MVC patterns
* Models are dicts, so dot-attribute or key access is valid.
* Support for specifiying Field() attributes without requiring
  them or enforcing types.
* Lazy-loading foreign key instances.
* (Hopefully) quick and lightweight.

Requirements
------------
* PyMongo - http://github.com/mongodb/mongo-python-driver

Installation
------------
You can install it from PyPI with (may need sudo):

    easy_install mogo

or

    pip install mogo

Alternatively you should be able to grab it via git and run the following 
command:
    
    python setup.py install
   
Tests
-----
To run the tests, make sure you have a MongoDB instance running
on your local machine. It will write and delete entries to 
mogotest db, so if by some bizarre coincidence you have / need that, 
you might want to alter the DBNAME constant in the mogo/tests.py
file.

After installation, or from the root project directory, run:

    python tests.py

Usage
-----
All the major classes and functions are available under mogo:

    import mogo
    # or
    from mogo import Model, Field, connect, ReferenceField

You should be able to immediately use this with any existing data
on a MongoDB installation. (DATA BE WARNED: THIS IS ALPHA!!) All you 
need is a class with the proper collection name, and connect to
the DB before you access it.
        
Yes, this means the most basic example is just a class with nothing:
    
    class NewModel(Model):
        pass
        
However, a Field class has been added for self-documenting purposes
(and features may be added later if necessary). You should pass in a
type as the first argument to a Field -- not for type checking on saving
or loading, but just for reference sake (and other libraries). All standard
types should work, as well as pymongo.objectid.ObjectId and 
pymongo.dbref.DBRef.

You can also pass an optional default=VALUE, where VALUE is either a 
static value like "foo" or 42, or it is a callable that returns a static
value like time.time() or datetime.now(). (Thanks @nod!)

The  ReferenceField class allows (simple) model references to be used. 
The "search" class method lets you pass in model instances and compare. 

So most real world models will look more this:

    class Company(Model):
        name = Field(unicode)
        age = Field(int)
        
        @property
        def people(self):
            return Person.search(company=self)

    class Person(Model):
        name = Field(unicode)
        email = Field(unicode)
        joined = Field(float, datetime.now)
        company = ReferenceField(Company)

...and simple usage would look like this:

    acme = Company(name="Acme, Inc.")
    acme.save()
    # Acme got a new employee. Congrats, Joe.
    joe = Person(name="Joe", email="joe@whaddyaknow.com")
    joe.company = acme
    joe.save()
    
    print [person.name for person in acme.people]
    # results in ["Joe",]
    print person.joined
    # results in something like 1300399372.87834
    
Note -- only use a ReferenceField if you have been storing
DBRef's as the values. If you've just been storing ObjectIds or 
something, it may be easier for existing data to just use 
a Field() and do the retrieval logic yourself.

Most of the basic collection methods are available on the model. Some
are classmethods, like .find(), .find_one(), .count(), etc. Others
simplify things like .save() (which handles whether to insert or update), 
but still take all the same extra parameters as PyMongo's objects. A few 
properties like .id provide shorthand access to standard keys. (You 
can overwrite what .id returns by setting _id_field on the class.) 
Finally, a few are restricted to class-only access, like Model.remove
and Model.drop (so you don't accidentally go wiping your collections
by calling a class method on an instance.)

The .order() on a find() or search() result gives you a shorthand
to the .sort() method (which is also available.) You can just do:

    Answers.search(value=42).order(question=ASC)

...and to order by additional constraints, add more orders:

    Animals.search().order(intelligence=ASC).order(digital_watches=DESC)

The following is a simple user model that hashes a password, followed by 
a usage example that shows some additional methods.

MODEL EXAMPLE:

    from mogo import Model, Field
    import hashlib
    import datetime

    class User(Model):
        # By default, it uses the lowercase class name. To override,
        # you can either set cls.__name__, or use _name:
        _name = 'useraccount'
        
        # Document fields are optional (and don't do much)
        # but you'll probably want them for documentation.
        name = Field(unicode)
        username = Field(unicode)
        password = Field(unicode)
        joined = Field(datetime, datetime.now)
    
        def set_password(self, password):
            hash_password = hashlib.md5(password).hexdigest()
            self.password = hash_password
            self.save()
        
        @classmethod
        def authenticate(cls, username, password):
            hash_password = hashlib.md5(password).hexdigest()
            return cls.find_one({
                'username':username, 
                'password':hash_password
            })
        

USAGE EXAMPLE

    from mogo import connect, ASC, DESC

    conn = connect('mydb') # takes host, port, etc. as well.
    
    # Inserting...
    new_user = User(username='test', name='Testing')
    # notice that we're setting a field "role" that we
    # did not specify in the Model definition.
    new_user.role = 'admin'
    new_user.set_password('f00b4r')
    new_id = new_user.save(safe=True) # using a PyMongo param
    user = User.grab(new_id) # grabs by ID

    # Probably not the best usage example... :)
    results = User.find({'role': 'admin'})
    for result in results:
        print result.username, result.name
        result.set_password('hax0red!')
        result.save() # only saves updated fields this time
        
    # Alternate searching
    test = User.search(name="Testing").first()
    # or...
    test = User.find_one({"name": "Malcome Reynolds"})
    # or to order...
    test = User.find().order(joined=DESC).order(name=ASC)
    
    # Deleting...
    test.delete()
    
    # Remove and drop class methods
    User.remove({'role': 'admin'}) # wipes all admins
    User.drop() # removes collection entirely

Scroll through the mogo/model.py file in the project to see the 
methods available. If something is not well documented, ping me at the
mailing list (see below).

TODO
----
* Write more tests
* Implement full PyMongo base compatibility
* Implement (optional) type-checking and defaults.
* Implement Map-Reduce and Group
* Maybe, MAYBE look at gridfs.
* Make faster where possible.

Contact
-------
* Mailing List Web: http://groups.google.com/group/mogo-python
* Mailing List Address: mogo-python@googlegroups.com

If you play with this in any way, I'd love to hear about it. It's
really, really alpha -- I still have some collection methods to add
to the base Model, and I haven't touched Map / Reduce results or
anything really advanced, but hopefully this scratches someone else's
itch too.
