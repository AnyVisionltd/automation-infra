#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from setuptools import setup, find_packages

if sys.version_info < (3, 6):
    raise RuntimeError("automation-infra requires Python 3.6+")

with open('README.md', mode='r', encoding='utf-8') as f:
    readme = f.read()

with open('requirements3.txt', mode='r', encoding='utf-8') as f:
    install_requires = f.read().splitlines()

setup(
    name='automation_infra',
    author='Ori Haberman',
    author_email='orielh@anyvision.co',
    maintainer='Ori Haberman',
    description='plugin which inits hardware reqs of a test with pytest_runtest_setup hook',
    long_description=readme,
    long_description_content_type='text/markdown',
    packages=find_packages(exclude=['tests']),
    python_requires='>=3.6',
    install_requires=install_requires,
    entry_points={
        'pytest11': [
            'automation_infra = pytest_automation_infra',
        ],
    },
)
