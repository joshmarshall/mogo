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

from distutils.core import setup

setup(
    name='mogo',
    version='0.5.1',
    description='Simple PyMongo "schema-less" object wrapper',
    author='Josh Marshall',
    author_email='catchjosh@gmail.com',
    url="http://github.com/joshmarshall/mogo/",
    license="http://www.apache.org/licenses/LICENSE-2.0",
    package_data={"mogo": ["py.typed"]},
    packages=['mogo', ],
    install_requires=["pymongo>=3.0"],
    zip_safe=False)
