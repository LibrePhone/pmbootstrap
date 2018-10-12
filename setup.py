#!/usr/bin/env python3

import re
import ast
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

from codecs import open
from os import path


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', 'Arguments to pass to pytest')]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''

    def run_tests(self):
        import shlex
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


here = path.abspath(path.dirname(__file__))
_version_re = re.compile(r'version\s+=\s+(.*)')

with open(path.join(here, 'pmb/config/__init__.py'), 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode('utf-8')).group(1)))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='pmbootstrap',
    version=version,
    description='A sophisticated chroot / build / flash tool to develop and install postmarketOS',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='postmarketOS Developers',
    author_email='info@postmarketos.org',
    url='https://www.postmarketos.org',
    license='GPLv3',
    python_requires='>=3.4',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='postmarketos pmbootstrap',
    packages=find_packages(exclude=['aports', 'keys', 'test']),
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
    extras_require={
        'completion': ['argcomplete'],
    },
    entry_points={
        'console_scripts': [
            'pmbootstrap=pmb:main',
        ],
    },
    include_package_data=True,
)
