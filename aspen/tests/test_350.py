import aspen
from aspen._configuration import Configuration, ConfigurationError
from aspen._configuration import validate_address


def test_validate_address():
    if aspen.WINDOWS:
        try:
            validate_address('.')
        except ConfigurationError:
            pass
    else:
        validate_address('.')


def test_want_daemon():
    configuration = Configuration(['start'])

