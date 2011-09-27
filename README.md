Mogo
====
This library is a simple "schema-less" object wrapper around the
pymongo library (http://github.com/mongodb/mongo-python-driver). Mogo
simply provides some simple helpers to use PyMongo in an MVC 
environment (thins like dot-attribute syntax, model methods, 
reference fields, etc.)

While pymongo is very simple to use and really flexible, it doesn't
fully meet the MVC pattern because you are working with plain dicts
and can't attach model logic anywhere.

Mogo is licensed under the Apache License, Version 2.0
(http://www.apache.org/licenses/LICENSE-2.0.html).

Features
--------
* Object oriented design for MVC patterns
* Models are dicts, so dot-attribute or key access is valid. Dot attribute
  gives "smart" values, key access gives "raw" pymongo values.
* Support for specifiying Field() attributes without requiring
  them or enforcing types.
* Simple ReferenceField implementation.
* (Hopefully) quick and lightweight.

Requirements
------------
* PyMongo - http://github.com/mongodb/mongo-python-driver

Installation
------------
You can install it from PyPI with:

```sh
pip mogo
```

or if you're old school:

```sh
easy_install mogo
```

Alternatively you should be able to grab it via git and run the following
command:

```sh
python setup.py install
```

Tests
-----
To run the tests, make sure you have a MongoDB instance running
on your local machine. It will write and delete entries to
mogotest db, so if by some bizarre coincidence you have / need that,
you might want to alter the DBNAME constant in the mogo/tests.py
file.

After installation, or from the root project directory, run:

```sh
nosettest tests/
```

If you don't have nose, it's available with:

```sh
pip install nose
```

Importing
---------

All the major classes and functions are available under the top level
mogo module:

```python
import mogo
# or
from mogo import Model, Field, connect, ReferenceField
```

Models
------
Models are subclasses of dicts with some predefined class and instance
methods. They are designed so that you should be able to use them
with an existing MongoDB project (DATA BE WARNED: THIS IS ALPHA!)
All you need is a class with the proper collection name, and connect
to the DB before you access it.

Yes, this means the most basic example is just a class with nothing:

```python
class Hero(Model):
    pass
```

You can now do things like:

```python
hero = Hero.find({"name": "Malcolm Reynolds"}).first()
```

By default, it will use the lowercase name of the model as the
collection name. So, in the above example, the equivalent pymongo
call would be:

```python
db.hero.find({"name": "Malcolm Reynolds"})[0]
```

Of course, Models are much more useful with methods:

```python
class Hero(Model):
    def swashbuckle(self):
        print "%s is swashbuckling!" % self["name"]

mal = Hero.find({"name": "Mal"}).first()
hero.swashbuckle()
# prints "Mal is swashbuckling!"
```

Since Models just subclass dictionaries, you can use (most) of the
normal dictionary methods (see `update` later on):

```python
hero = Hero.find_one({"name": "Book"})
hero.get("powers", ["big darn hero"]) # returns ["big darn hero"]
hero_dict = hero.copy()
for key, value in hero.iteritems():
    print key, value
```

To save or update values in the database, you use either `save` or
`update`. (Imagine that.) If it is a new object, you have to `save`
it first:

```python
mal = Hero(name="Malcom Reynolds")
mal.save()
```

`save` will always overwrite the entire entry in the database.
This is the same behavior that PyMongo uses, and it is helpful for
simpler list and dictionary usage:

```python
zoe = Hero(name="Zoe", powers=["warrior woman"])
zoe.save()
zoe["powers"].append("big darn hero")
zoe.save()
```

...however, this can ultimately be inefficient, not to
mention produce race conditions and have people saving over each
other's changes.

This is where `update` comes in. Note that the `update` method does
NOT function like the dictionary method. It has two roles, 
depending on whether it is called from a class or from an instance.

If it is called from a class, it just passes everything on to PyMongo
like you might expect:

```python
Hero.update({"name": "Malcolm Reynolds"},
    {"$set":{"name": "Capt. Tightpants"}}, safe=True)
# equals the following in PyMongo
db.hero.update({"name": "Malcolm Reynolds"},
    {"$set":{"name": "Capt. Tightpants"}}, safe=True)
```

If it is called from an instance, it uses keyword arguments to set
attributes, and then sends off a PyMongo "$set" update:

```python
hero = Hero.find_one({"name": "River Tam"})
hero.update(powers=["telepathy", "mystic weirdness"])
# equals the following in PyMongo
hero = db.hero.find_one({"name": "River Tam"})
db.hero.update({"_id": hero["_id"]},
    {"$set": {"powers": ["telepathy", "mystic weirdness"]}})
```

Fields
------
Using a Field is (usually) necessary for a number of reasons. While
you can remain completely schemaless in Mongo, you will probably go
a little nutty if you don't document the standard top level fields
you are using.

Fields just go on the model like so:

```python
class Hero(Model):
    name = Field()
```

...and enable dot-attribute access, as well as some other goodies.
Fields take several optional arguments -- the first argument is a
type, and if used the field will validate any value passed as an
instance of that (sub)class. For example:

```python
class Hero(Model):
    name = Field(unicode)

# the following will raise a ValueError exception...
wash = Hero(name="Wash")
# but this is fine
wash = Hero(name=u"Wash")
```

If you don't want this validation, just don't pass in any type. If you
want to customize getting and setting, you can pass in  `set\_callback`
and `get\_callback` functions to the Field constructor:

```python
class Ship(Model):
    type = Field(set_callback=lambda x: "Firefly")

ship = Ship(type="firefly")
print ship.type #prints "Firefly"
ship.type =  "NCC 1701"
print ship.type #prints "Firefly"
# overwriting the "real" stored value
ship["type"] = "Millenium Falcon"
print ship.type # prints "Millenium Falcon"
```

You can also pass an optional default=VALUE, where VALUE is either a
static value like "foo" or 42, or it is a callable that returns a static
value like time.time() or datetime.now(). (Thanks @nod!)

```python
class Ship(Model):
    name = Field(unicode, default=u"Dormunder")
```

ReferenceField
--------------
The  ReferenceField class allows (simple) model references to be used.
The "search" class method lets you pass in model instances and compare.

So most real world models will look more this:

```python
class Ship(Model):
    name = Field(unicode, required=True)
    age = Field(int, default=10)
    type = Field(unicode, default="Firefly")

    @classmethod
    def new(cls, name):
        """ Creating a strict interface for new models """

    @property
    def crew(self):
        return Crew.search(ship=self)

class Crew(Model):
    name = Field(unicode, required=True)
    joined = Field(float, default=datetime.now, required=True)
    ship = ReferenceField(Ship)
```

...and simple usage would look like this:

```python
serenity = Ship.new(u"Serenity")
serenity.save()
mal = Crew(name=u"Malcom Reynolds", ship=None)
mal.sav()
mal.ship = serenity
mal.save()

print [person.name for person in serenity.crew]
# results in [u"Malcom Reynolds",]
print mal.joined
# prints out the datetime that the instance was created
```

Note -- only use a ReferenceField with legacy data if you have been
storing DBRef's as the values. If you've just been storing ObjectIds or
something, it may be easier for existing data to just use a Field() with
a `(set|get)\_callback` do the retrieval logic yourself.


PolyModels
----------
MongoDB lets you store any fields in any collection -- this means it is
particularly well suited for storing and querying across inheritance 
relationships. I've recently added a new model type of `PolyModel` that
lets you define this in a (hopefully) simple way.

```python
class Person(PolyModel):
    """ The 'base' person model """
    name = Field(unicode, required=True)
    role = Field(unicode, default=u"person")

    # custom method
    def is_good(self):
        """ All people are innately good. :) """
        return True

    # required to determine what `type` something is
    def get_model_key(self):
        return "role"
```

As you can see, we use the "role" field to determine what type a person
is -- by default, they are all just "person" and therefore should return
a Person instance. We need to register some new people types:

```python
@Person.register
class Villain(Person):
    role = Field(unicode, default=u"villain")

    # Overwriting method
    def is_good(self):
        """ All villains are not good """
        return False

@Person.register("questionable")
class FlipFlopper(Person):
    role = Field(unicode, default=u"questionable")
    alliance = Field(unicode, default=u"good")

    def is_good(self):
        return self.alliance == "good"

    def trade_alliance(self):
        if self.alliance == "good":
            self.alliance = "bad"
        else:
            self.alliance = "good"
        self.save()
```

The PolyModel.register decorator takes an optional value argument, which
is what is used to compare to the field specified by `get_model_key` in
the base model. It works with the following pseudo-logic:

* Create a new Person instance (either from the DB or __init__)
* key = Person.get_model_key() # in this case, it's "role"
* Get current value of "role" (or use the default)
* Check the registered models, find one that matches the role value
* If a registered model class is found, use that.
* Otherwise, use the base class (Person in this case)

Using the above classes that we created / registered, here's a usage example:

```python
simon = Person(name="Simon Tam")
simon.save()
simon.is_good() # True
badger = Villain(name="Badger")
badger.save()
badger.is_good() # False
jayne = FlipFlopper(name="Jayne")
jayne.save()

Person.find().count() # should be 3
jayne = Person.find(name="Jayne")
isinstance(jayne, FlipFlopper) # True
jayne.is_good() # True
jayne.trade_alliance()
jayne.is_good() # False

Villain.find().count() # should be 1
```

Extra Verbage (i.e. stuff I haven't rewritten yet)
--------------------------------------------------
Most of the basic collection methods are available on the model. Some
are classmethods, like .find(), .find\_one(), .count(), etc. Others
simplify things like .save() (which handles whether to insert or update),
but still take all the same extra parameters as PyMongo's objects. A few
properties like .id provide shorthand access to standard keys. (You
can overwrite what .id returns by setting \_id\_field on the class.)
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
    new_user = User.new(username=u'test', name=u'Testing')
    # notice that we're setting a field "role" that we
    # did not specify in the Model definition.
    new_user["role"] = u'admin'
    new_user.set_password(u'f00b4r')
    new_id = new_user.save(safe=True) # using a PyMongo param
    user = User.grab(new_id) # grabs by ID

    # Probably not the best usage example... :)
    results = User.find({'role': 'admin'})
    for result in results:
        print result.username, result.name
        result.set_password('hax0red!')
        result.save() # only saves updated fields this time

    # TODO: Document updating...

    # Alternate searching
    test = User.search(name=u"Testing").first()
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
* Implement Map-Reduce and Group
* Maybe, MAYBE look at gridfs.
* Make faster where possible.

Contact
-------
* Mailing List Web: http://groups.google.com/group/mogo-python
* Mailing List Address: mogo-python@googlegroups.com

If you play with this in any way, I'd love to hear about it. I still
have some collection methods to add to the base Model, and I haven't
touched Map / Reduce results or anything really advanced, but
hopefully this scratches someone else's itch too.
