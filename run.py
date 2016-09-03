# coding=utf-8

"""
This script makes it possible to debug the cards.py module in PyCharm.

Set up a build configuration targeting this script and the module becomes runnable/debuggable.

Note that when targeting this script, the build configuration should *not* specify the -m argument.
"""

import sys
import os
import runpy

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')

sys.path.insert(0, path)

runpy.run_module('cards', run_name="__main__", alter_sys=True)
