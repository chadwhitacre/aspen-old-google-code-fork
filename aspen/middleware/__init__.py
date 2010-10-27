import os

from aspen import colon
from aspen.exceptions import MiddlewareConfError


clean = lambda x: x.split('#',1)[0].strip() # clears comments & whitespace


def load(root):
    """Given a string, return a list of middleware callables in reverse order.
    """

    # Find a config file to parse.
    # ============================

    default_stack = []
    confpath = os.path.join(root, '__', 'etc', 'middleware.conf')
    if not os.path.isfile(confpath):
        log.info("No middleware configured.")
        return default_stack


    # We have a config file; proceed.
    # ===============================

    fp = open(confpath)
    lineno = 0
    stack = []

    for line in fp:
        lineno += 1
        name = clean(line)
        if not name:                            # blank line
            continue
        else:                                   # specification
            obj = colon.colonize(name, fp.name, lineno)
            if not callable(obj):
                msg = "'%s' is not callable" % name
                raise MiddlewareConfError(msg, lineno)
            stack.append(obj)

    stack.reverse()
    return stack
