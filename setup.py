#!/usr/bin/env python

from distutils.core import setup

setup(
    name='mogo',
    version='0.1',
    description='Really simple PyMongo "ORM" wrapper',
    author='Josh Marshall',
    author_email='catchjosh@gmail.com',
    packages=['mogo',],
    requires=['pymongo',]
)