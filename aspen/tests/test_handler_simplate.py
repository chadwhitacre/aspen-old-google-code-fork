import os.path
import time

from aspen.tests import assert_raises
from aspen.tests import fsfix # importing as module to extend somewhat
from jinja2 import Template


# Fixture
# =======

def start_response(status, headers, exc=None):
    def write():
        return status, headers
    return write

INDEX_HTML = fsfix.path('fsfix', 'index.html')
WSGI_ARGS = ({'PATH_TRANSLATED':INDEX_HTML}, start_response)

def stdlib(*args):
    """Given args, return a stdlib-flavored simplate

    Need lazy import because importing aspen.handlers.simplates requires that
    aspen be configured.

    """
    from aspen.handlers.simplates import stdlib
    return stdlib(*args)


# Tests
# =====

def test_cache():
    fsfix.mk( ('__/etc/aspen.conf', "[main]\nmode=production")
            , ('index.html', "Greetings, perl!")
            , configure=True
             )

    from aspen.handlers import simplates

    expected = 'Greetings, perl!'
    actual = simplates.load_cached(INDEX_HTML)[3].render()
    assert actual == expected, actual
    first = simplates.__cache[INDEX_HTML].modtime

    time.sleep(2)
    open(INDEX_HTML, 'w+').write('Greetings, python!')

    expected = 'Greetings, python!'
    actual = simplates.load_cached(INDEX_HTML)[3].render()
    assert actual == expected, actual
    second = simplates.__cache[INDEX_HTML].modtime

    assert second > first, (first, second)


# Teardown
# ========

fsfix.attach_teardown(globals())
