#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
from setuptools import setup


setup(
    name='pytest-automation_infra',
    author='Ori Haberman',
    author_email='orielh@anyvision.co',
    maintainer='Ori Haberman',
    description='plugin which inits hardware reqs of a test with pytest_runtest_setup hook',
    py_modules=['pytest_automation_infra'],
    install_requires=['pytest>=3.5.0'],
    entry_points={
        'pytest11': [
            'automation_infra = pytest_automation_infra',
        ],
    },
)
