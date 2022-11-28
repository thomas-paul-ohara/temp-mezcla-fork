#! /usr/bin/env python
#
# Notes:
# - Simple installer for subset of scripts under Github
#       https://github.com/tomasohara/misc-utility
# - Based on following:
#       https://stackoverflow.com/questions/1471994/what-is-setup-py
#

"""Simple installer"""

from distutils.core import setup

setup(name='Mezcla',
      packages=['mezcla'],
      module="mezcla",
      version='1.3.4',
      description-file="README.txt",
      dist-name="Mezcla",
      ## OLD: py_modules=PYTHON_MODULE_NAMES,
      author="Tom O'Hara",
      # TODO: find out which email key is preferred
      email="tomasohara@gmail.com",
      author-email="tomasohara@gmail.com"
      requires-python=">=3.6",
      ## TODO:
      ## install_requires=["six"],
      home-page="https://github.com/tomasohara/Mezcla",
      classifiers=[
          "License :: OSI Approved :: LGPLv3",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.7",
      ]
      description="""
Package with core modules from https://github.com/tomasohara/misc-utility
note: mezcla is Spanish for mixture.
""")

[tool.flit.scripts]
realpython = "mezcla.__main__:main"
