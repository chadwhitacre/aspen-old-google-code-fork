"""Simplates
"""
import mimetypes
import os
from os.path import exists, isfile

import os
import stat
import threading
import traceback
import sys

import util
from jinja2 import Environment, FileSystemLoader, Template


FORM_FEED = chr(12) # == '\x0c', ^L, ASCII page break
ENCODING = 'UTF-8'
MODE_STPROD = True 
MODE_DEBUG = False


class LoadError(StandardError):
    """Represent a problem parsing a simplate.
    """


# Cache helpers
# =============

class Entry:
    """An entry in the global simplate cache.
    """

    fspath = ''         # The filesystem path [string]
    modtime = None      # The timestamp of the last change [datetime.datetime]
    lock = None         # Access control for this record [threading.Lock]
    quadruple = None    # A post-processed version of the data [4-tuple]
    exc = None          # Any exception in reading or compilation [Exception]

    def __init__(self):
        """Populate with dummy data or an actual db entry.
        """
        self.fspath = ''
        self.modtime = 0
        self.lock = threading.Lock()
        self.quadruple = ()


class Locks:
    checkin = threading.Lock()
    checkout = threading.Lock()


__cache = dict()        # cache
__locks = Locks()       # access controls for __cache


# Core loader
# ===========

def load_simplate_uncached(fspath):
    """Given a filesystem path, return three objects (uncached).

    A simplate is a template with two optional Python components at the head of
    the file, delimited by '^L'. The first Python section is exec'd when the
    simplate is first called, and the namespace it populates is saved for all
    subsequent runs (so make sure it is thread-safe!). The second Python
    section is exec'd within the template namespace each time the template is
    rendered.

    If the mimetype does not start with 'text/', then it is only a simplate if
    it has at least one form feed in it. Binary files generally can't be
    decoded using UTF-8. If Python's mimetypes module doesn't know about a
    certain extension, then we default to application/octet-stream.

    """

    simplate = open(fspath).read()
    
    mimetype = mimetypes.guess_type(fspath, 'text/plain')[0]
    if mimetype is None:
        mimetype = 'application/octet-stream'
    if not mimetype.startswith('text/'):
        if FORM_FEED not in simplate:
            return (mimetype, None, None, simplate) # static file; exit early

    simplate = simplate.decode(ENCODING)


    nform_feeds = simplate.count(FORM_FEED)
    if nform_feeds == 0:
        script = imports = ""
        template = simplate
    elif nform_feeds == 1:
        imports = ""
        script, template = simplate.split(FORM_FEED)
    elif nform_feeds == 2:
        imports, script, template = simplate.split(FORM_FEED)
    else:
        raise SyntaxError( "Simplate <%s> may have at most two " % fspath
                         + "form feeds; it has %d." % nform_feeds
                          )


    # Standardize newlines.
    # =====================
    # compile requires \n, and doing it now makes the next line easier.

    imports = imports.replace('\r\n', '\n')
    script = script.replace('\r\n', '\n')


    # Pad the beginning of the script section so we get accurate tracebacks.
    # ====================================================================

    script = ''.join(['\n' for n in range(imports.count('\n'))]) + script


    # Prep our cachable objects and return.
    # =====================================

    namespace = dict()
    namespace['__file__'] = fspath
    script = compile(script, fspath, 'exec')
    if template.strip():
        template = Template(template)
    else:
        template = None

    exec compile(imports, fspath, 'exec') in namespace

    return (mimetype, namespace, script, template)


# Cache wrapper
# =============

def load_simplate_cached(fspath):
    """Given a filesystem path, return three objects (with caching).
    """

    # Check out an entry.
    # ===================
    # Each entry has its own lock, and "checking out" an entry means
    # acquiring that lock. If a simplate isn't yet in our cache, we first
    # "check in" a new dummy entry for it (and prevent other threads from
    # adding the same simplate), which will be populated presently.

    #thread_id = threading.currentThread().getName()[-1:] # for debugging
    #call_id = ''.join([random.choice(string.letters) for i in range(5)])

    __locks.checkout.acquire()
    try: # critical section
        if fspath in __cache:

            # Retrieve an already cached simplate.
            # ====================================
            # The cached entry may be a dummy. The best way to guarantee we
            # will catch this case is to simply refresh our entry after we
            # acquire its lock.

            entry = __cache[fspath]
            entry.lock.acquire()
            entry = __cache[fspath]

        else:

            # Add a new entry to our cache.
            # =============================

            dummy = Entry()
            dummy.fspath = fspath
            dummy.lock.acquire()
            __locks.checkin.acquire()
            try: # critical section
                if fspath in __cache:
                    # Someone beat us to it. @@: can this actually happen?
                    entry = __cache[fspath]
                else:
                    __cache[fspath] = dummy
                    entry = dummy
            finally:
                __locks.checkin.release()

    finally:
        __locks.checkout.release() # Now that we've checked out our simplate, 
                                   # other threads are free to check out other 
                                   # simplates.


    # Process the simplate.
    # =====================

    try: # critical section

        # Decide whether it's a hit or miss.
        # ==================================

        modtime = os.stat(fspath)[stat.ST_MTIME]
        if entry.modtime == modtime:                            # cache hit
            if entry.exc is not None:
                raise entry.exc
        else:                                                   # cache miss
            try:
                entry.quadruple = load_simplate_uncached(fspath)
                entry.exc = None
            except Exception, exception:
                # NB: Old-style string exceptions will still raise.
                entry.exc = ( LoadError(traceback.format_exc())
                            , sys.exc_info()[2]
                             )


        # Check the simplate back in.
        # ===========================

        __locks.checkin.acquire()
        try: # critical section
            entry.modtime = modtime
            __cache[fspath] = entry
            if entry.exc is not None:
                raise entry.exc[0]
        finally:
            __locks.checkin.release()

    finally:
        entry.lock.release()


    # Return
    # ======
    # Avoid mutating the cached namespace dictionary.

    mimetype, namespace, script, template = entry.quadruple
    if namespace is not None:
        namespace = namespace.copy()
    return (mimetype, namespace, script, template)

