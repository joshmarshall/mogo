#!/usr/bin/env python
"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from setuptools import setup, find_packages

with open("VERSION") as version_fp:
    VERSION = version_fp.read().strip()

setup(
    name="mogo",
    version=VERSION,
    description="Simple PyMongo \"schema-less\" object wrapper",
    author="Josh Marshall",
    author_email="catchjosh@gmail.com",
    url="http://github.com/joshmarshall/mogo/",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    packages=find_packages(exclude=["tests", "dist"]),
    install_requires=["pymongo>=3.0", ],
    classifiers=["Development Status :: 3 - Alpha"])
