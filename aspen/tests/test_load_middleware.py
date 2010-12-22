import os
import sys

from aspen.tests import assert_raises
from aspen.tests.fsfix import mk, attach_teardown
from aspen.exceptions import *
from aspen import middleware


# Fixture
# =======

import random
import string

lib_python = os.path.join('__', 'lib', 'python%s' % sys.version[:3])
sys.path.insert(0, os.path.join('fsfix', lib_python))

class Paths:
    pass

def load():
    return middleware.load('fsfix')


# No middleware configured
# ========================

def test_no_magic_directory():
    expected = []
    actual = load()
    assert actual == expected, actual

def test_no_file():
    mk('__/etc')
    expected = []
    actual = load()
    assert actual == expected, actual

def test_empty_file():
    mk('__/etc', ('__/etc/middleware.conf', ''))
    expected = []
    actual = load()
    assert actual == expected, actual


# Middleware configured
# =====================

def test_something():
    mk('__/etc', ('__/etc/middleware.conf', 'random:choice'))
    expected = [random.choice]
    actual = load()
    assert actual == expected, actual

def test_must_be_callable():
    mk('__/etc', ('__/etc/middleware.conf', 'string:digits'))
    err = assert_raises(MiddlewareConfError, load)
    assert err.msg == "'string:digits' is not callable"

def test_order():
    mk('__/etc', ('__/etc/middleware.conf', 'random:choice\nrandom:seed'))
    expected = [random.seed, random.choice]
    actual = load()
    assert actual == expected, actual


# Basics
# ======

def test_blank_lines_skipped():
    mk('__/etc', ('__/etc/middleware.conf', '\n\nrandom:choice\n\n'))
    expected = [random.choice]
    actual = load()
    assert actual == expected, actual

def test_comments_ignored():
    mk('__/etc', ('__/etc/middleware.conf', """

        #comment
        random:choice#comment
        random:sample # comments

        """))
    expected = [random.sample, random.choice]
    actual = load()
    assert actual == expected, actual


# Remove the filesystem fixture after each test.
# ==============================================

attach_teardown(globals())
