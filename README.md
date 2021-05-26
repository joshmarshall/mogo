[![Build Status](https://circleci.com/gh/joshmarshall/mogo.svg?style=svg)](https://circleci.com/gh/joshmarshall/mogo)
Mogo
====
This library is a simple "schema-less" object wrapper around the
pymongo library (http://github.com/mongodb/mongo-python-driver).
Mogo provides helpers to use PyMongo in an MVC environment
(things like dot-attribute syntax, model methods,
reference fields, etc.)

While pymongo is straightforward to use and really flexible, it
doesn't help with MVC because you are working with plain dicts
and can't attach model logic anywhere.

Mogo is licensed under the Apache License, Version 2.0
(http://www.apache.org/licenses/LICENSE-2.0.html).

## RELEASE NOTES ##
As of the most recent release (0.5.0+), this only supports Python 3.5+, and
PyMongo 3.0+. If you are upgrading, be sure to test thoroughly, as internals
have changed somewhat, and PyMongo has deprecated a number of methods and
arguments.


Features
--------
* Put classes / structure around pymongo results
* Models are dicts, so dot-attribute or key access is valid. Dot attribute
  gives "smart" values, key access gives "raw" pymongo values.
* Support for specifiying Field() attributes without requiring
  them or enforcing types.
* Simple ReferenceField implementation.

Requirements
------------
* Python 3.5+
* PyMongo - http://github.com/mongodb/mongo-python-driver

Installation
------------
You can install it from PyPI with:

```sh
pip install mogo
```

Alternatively you should be able to grab it via git and run the following
command:

```sh
python setup.py install
```

Tests
-----
To run the tests, make sure you have a MongoDB instance running
on your local machine. It will write and delete entries to the
`_mogotest` db, so if by some bizarre coincidence you have / need that,
you might want to alter the DBNAME constant in the mogo/tests.py
file.

You will also need `mypy` and `flake8` if you are running the full suite of
typechecking and linting.

After installation, or from the root project directory, run:

```sh
make test
```

... to run typechecking, linting, and the unit / integration tests.


Alternatively, you can run just the unit / integration tests with:

```sh
pytest tests/
```

If you don't have pytest, it's available with:

```sh
pip install pytest
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

Connecting
----------

Mogo uses a single global connection, so that once you connect, you can
just start accessing your model class methods. Connecting looks like:


```python
from mogo import connect

connect("my_database") # connects to a local mongodb server with default port
connect("foobar", "mongodb://127.0.0.1:28088")
connect(uri="mongodb://user:pass@192.168.0.5/awesome") # for heroku, etc.
```

If you need to use an alternate connection for a chunk of code, without
losing your main connection, you can use the following style:

```python
from mogo import connect, session

connect("my_awesome_database")
# do normal stuff
with mogo.session("my_alternate_database"):
    # do stuff with other database
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
    def swashbuckle(self) -> None:
        print("%s is swashbuckling!" % self["name"])

mal = Hero.find({"name": "Mal"}).first()
mal.swashbuckle()
# prints "Mal is swashbuckling!"
```

Since Models just subclass dictionaries, you can use (most) of the
normal dictionary methods (see `update` later on):

```python
hero = Hero.find_one({"name": "Book"})
hero.get("powers", ["big darn hero"]) # returns ["big darn hero"]
hero_dict = hero.copy()
for key, value in hero.iteritems():
    print(key, value)
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

(BETA) If you call it from a cursor, it will use the query you
originally provided to the cursor. This does not currently respect
additional filtering like `where()`, does not check types when
setting values, and has not been exhaustively tested. (So beware.)

```python
hero_cursor = Hero.find({"name": {"$in": ["River", "Simon"]}})
hero_cursor.update({"$push": {"powers": "siblingness"}})
# or, for you keyword-liking people...
hero_cursor.change(powers="siblingness")
```

Fields
------
Using a Field is (usually) necessary for a number of reasons. While
you can remain completely schemaless in Mongo, you will probably go
a little nutty if you don't document the standard top level fields
you are using.

Fields just go on the model like so (including optional type annotations):

```python
from typing import Any

class Hero(Model):
    name = Field[Any]()
```

...and enable dot-attribute access, as well as some other goodies.
Fields take several optional arguments -- the first argument is a
type, and if used the field will validate any value passed as an
instance of that (sub)class. For example:

```python
class Hero(Model):
    name = Field[str](str)

# the following will raise a ValueError exception...
wash = Hero(name=b"Wash")
# but this is fine
wash = Hero(name="Wash")
```

If you don't want this validation, just don't pass in any type. If you
want to customize getting and setting, you can pass in  `set\_callback`
and `get\_callback` functions to the Field constructor:

```python
class Ship(Model):
    type = Field(set_callback=lambda x: "Firefly")

ship = Ship(type="firefly")
print(ship.type) #prints "Firefly"
ship.type = "NCC 1701"
print(ship.type) # prints "Firefly"
# overwriting the "real" stored value
ship["type"] = "Millenium Falcon"
print(ship.type) # prints "Millenium Falcon"
```

You can also pass an optional default=VALUE, where VALUE is either a
static value like "foo" or 42, or it is a callable that returns a static
value like time.time() or datetime.now(). (Thanks @nod!)

```python
class Ship(Model):
    name = Field[str](str, default="Dormunder")
```

ReferenceField
--------------
The  ReferenceField class allows (simple) model references to be used.
The "search" class method lets you pass in model instances and compare.

So most real world models will look more this:

```python
from mogo.cursor import Cursor

class Ship(Model):
    name = Field[str](str, required=True)
    age = Field[int](int, default=10)
    type = Field[str](str, default="Firefly")

    @classmethod
    def new(cls, name) -> "Ship":
        """ Creating a strict interface for new models """

    @property
    def crew(self) -> Cursor["Crew"]:
        return Crew.search(ship=self)

class Crew(Model):
    name = Field[str](str, required=True)
    joined = Field[float](float, default=datetime.now, required=True)
    ship = ReferenceField(Ship)
```

...and simple usage would look like this:

```python
serenity = Ship.create(name="Serenity")
mal = Crew.create(name="Malcom Reynolds", ship=None)
mal.ship = serenity
mal.save()

print([person.name for person in serenity.crew])
# results in ["Malcom Reynolds",]
print(mal.joined)
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
    name = Field[str](str, required=True)
    role = Field[str](str, default="person")

    # custom method
    def is_good(self) -> bool:
        """ All people are innately good. :) """
        return True

    # required to determine what `type` something is
    def get_model_key(self) -> str:
        return "role"
```

As you can see, we use the "role" field to determine what type a person
is -- by default, they are all just "person" and therefore should return
a Person instance. We need to register some new people types:

```python
@Person.register
class Villain(Person):
    role = Field[str](str, default="villain")

    # Overwriting method
    def is_good(self) -> bool:
        """ All villains are not good """
        return False

@Person.register("questionable")
class FlipFlopper(Person):
    role = Field[str](str, default="questionable")
    alliance = Field[str](str, default="good")

    def is_good(self) -> bool:
        return self.alliance == "good"

    def trade_alliance(self) -> None:
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
* key = `Person.get_model_key()` # in this case, it's "role"
* Get current value of "role" (or use the default)
* Check the registered models, find one that matches the role value
* If a registered model class is found, use that.
* Otherwise, use the base class (Person in this case)

Using the above classes that we created / registered, here's a usage example:

```python
simon = Person.create(name="Simon Tam")
simon.is_good() # True
badger = Villain.create(name="Badger")
badger.is_good() # False
jayne = FlipFlopper.create(name="Jayne")

Person.find().count() # should be 3
jayne = Person.find(name="Jayne")
isinstance(jayne, FlipFlopper) # True
jayne.is_good() # True
jayne.trade_alliance()
jayne.is_good() # False

Villain.find().count() # should be 1
```

Contact
-------
* Mailing List Web: http://groups.google.com/group/mogo-python
* Mailing List Address: mogo-python@googlegroups.com

If you play with this in any way, I'd love to hear about it.
