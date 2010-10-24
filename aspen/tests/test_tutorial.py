import os
import signal
import socket
import stat
import subprocess
import sys
import time
import urllib

import aspen
from aspen._configuration import Configuration
from aspen.exceptions import *
from aspen.tests import Block, assert_, assert_actual, assert_raises
from aspen.tests import hit_with_timeout
from aspen.tests.fsfix import mk, attach_teardown
from aspen.website import Website as _Website
from nose import SkipTest


# Fixture
# =======

if 'win32' == sys.platform:
    raise SkipTest # skip for now until we feel like putting aspen on PATH


class DummyServer:
    pass

def Website():
    config = Configuration(['--root=fsfix'])
    config.load_plugins()
    server = DummyServer()
    server.configuration = config
    return _Website(server)

class Aspen(Block):
    """Encapsulate a running aspen server.
    """

    def __init__(self):
        proc = subprocess.Popen( [ 'aspen' # assumed to be on PATH
                                 , '--address=:53700'
                                 , '--root=fsfix'
                                 , '--mode=production'
                                 , '--log-level=NIRVANA'
                                  ]
                                )
        self.proc = proc

    def getpid(self):
        return self.proc.pid

    def hit_and_terminate(self, path='/'):
        url = "http://localhost:53700" + path
        output = hit_with_timeout(url)
        os.kill(self.proc.pid, signal.SIGTERM)
        self.stop(self.proc.pid)
        return output


# Tests
# =====

def test_greetings_program():
    mk(('index.html', "Greetings, program!"))
    aspen = Aspen()
    expected = "Greetings, program!"
    actual = aspen.hit_and_terminate()
    assert actual == expected, actual


def test_your_first_handler():

    def setup():
        mk( ('__/lib/python/handy.py', """\
def handle(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [environ['PATH_TRANSLATED']]
    """)
          , ('__/etc/handlers.conf', """\
fnmatch aspen.rules:fnmatch

[handy:handle]
fnmatch *.asp
    """)
          , ('handled.asp', "Greetings, program?")
            )

    PATH_TRANSLATED = os.path.realpath(os.path.join('fsfix', 'handled.asp'))


    # Hit it from the inside.
    # =======================

    setup()
    expected = [PATH_TRANSLATED]
    actual = Website()({'PATH_INFO':'handled.asp'}, lambda a,b:a)
    yield assert_actual, expected, actual


    # Then hit it from the outside.
    # =============================

    setup()
    expected = PATH_TRANSLATED
    aspen = Aspen()
    actual = aspen.hit_and_terminate('/handled.asp')
    yield assert_actual, expected, actual


def test_auto_index():
    mk('FOO', '__')
    aspen = Aspen()
    actual = aspen.hit_and_terminate()
    yield assert_, 'FOO' in actual
    yield assert_, '__' not in actual


attach_teardown(globals())
