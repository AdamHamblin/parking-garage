#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Setup file for parking-garage.

    This file was generated with PyScaffold 3.0.3.
    PyScaffold helps you to put up the scaffold of your new Python project.
    Learn more under: http://pyscaffold.org/
"""

from setuptools import setup

# Add here console scripts and other entry points in ini-style format
entry_points = """
[console_scripts]
# script_name = parking-garage.module:function
# For example:
# fibonacci = parking-garage.skeleton:run
"""


def setup_package():
    setup(setup_requires=['pyscaffold>=3.0a0,<3.1a0'],
          entry_points=entry_points,
          use_pyscaffold=True)


if __name__ == "__main__":
    setup_package()
