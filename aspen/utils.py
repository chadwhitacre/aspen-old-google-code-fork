import datetime
import inspect
import math
import os
import re
import string
import time
import urllib
from os.path import isdir, isfile, join, realpath


INITIAL = '_' + string.letters
INNER = INITIAL + string.digits
def is_valid_identifier(s):
    """Given a string of length > 0, return a boolean.

        >>> is_valid_identifier('.svn')
        False
        >>> is_valid_identifier('svn')
        True
        >>> is_valid_identifier('_svn')
        True
        >>> is_valid_identifier('__svn')
        True
        >>> is_valid_identifier('123')
        False
        >>> is_valid_identifier('r123')
        True

    """
    try:
        assert s[0] in INITIAL
        assert False not in [x in INNER for x in s]
        return True
    except AssertionError:
        return False


def _is_callable_instance(o):
    return hasattr(o, '__class__') and hasattr(o, '__call__')

def cmp_routines(f1, f2):
    """Given two callables, return a boolean. Used in testing.
    """
    try:
        if inspect.isclass(f1):
            assert inspect.isclass(f2)
            assert f1 == f2
        elif inspect.ismethod(f1):
            assert inspect.ismethod(f2)
            assert f1.im_class == f2.im_class
        elif inspect.isfunction(f1):
            assert inspect.isfunction(f2)
            assert f1 == f2
        elif _is_callable_instance(f1):
            assert _is_callable_instance(f2)
            assert f1.__class__ == f2.__class__
        else:
            raise AssertionError("These aren't routines.")
        return True
    except AssertionError:
        return False


# Paths
# =====

def check_trailing_slash(environ, start_response):
    """Given WSGI stuff, return None or 301.

    environ must have PATH_TRANSLATED set in addition to PATH_INFO, which
    latter is required by the spec.

    """
    fs = environ['PATH_TRANSLATED']
    url = environ['PATH_INFO']
    if isdir(fs) and not url.endswith('/'):
        environ['PATH_INFO'] += '/'
        new_url = full_url(environ)
        start_response( '301 Moved Permanently'
                      , [('Location', new_url)]
                       )
        return ['Resource moved to: ' + new_url]


def find_default(defaults, fspath):
    """Given a list of defaults and a filesystem path, return a filesystem path.

    This function returns the new filesystem path, or the old one if no default
    is found.

    """
    if isdir(fspath):
        default = None
        for name in defaults:
            _path = join(fspath, name)
            if isfile(_path):
                default = _path
                break
        if default is not None:
            fspath = default
    return fspath


def full_url(environ):
    """Given a WSGI environ, return the full URL of the request.

    Adapted from Ian Bicking's recipe in PEP 333.

    """

    # Start building the URL.
    # =======================
    # http://

    url = [environ['wsgi.url_scheme'], '://']


    # Get the host.
    # =============
    # http://example.com

    port = None
    if environ.get('HTTP_X_FORWARDED_HOST'):    # try X-Forwarded-Host header
        host = environ['HTTP_X_FORWARDED_HOST']
    elif environ.get('HTTP_HOST'):              # then try Host header
        host = environ['HTTP_HOST']
    else:                                       # fall back to SERVER_NAME
        host = environ['SERVER_NAME']
        port = environ['SERVER_PORT']


    # Get the port.
    # =============
    # http://example.com:8080

    if port is None: # i.e., using X-Forwarded-Host or Host
        if ':' in host:
            assert host.count(':') == 1 # sanity check
            host, port = host.split(':')
        else:
            port = (environ['wsgi.url_scheme'] == 'http') and '80' or '443'


    # Add host and port to the url.
    # =============================

    url.append(host)
    if environ['wsgi.url_scheme'] == 'https':
        if port != '443':
           url.extend([':', port])
    else:
        assert environ['wsgi.url_scheme'] == 'http' # sanity check
        if port != '80':
           url.extend([':', port])


    # Add any path info and querystring.
    # ==================================
    # http://example.com:8080/foo/bar?baz=buz

    script_name = urllib.quote(environ.get('SCRIPT_NAME', ''))
    path_info = urllib.quote(environ.get('PATH_INFO', ''))
    if script_name == path_info == '':
        url.append('/')
    else:
        url.extend([script_name, path_info])
    if environ.get('QUERY_STRING'):
        url.extend(['?', environ['QUERY_STRING']])


    # Put it all together.
    # ====================

    return ''.join(url)


def translate(root, url):
    """Translate a URL to the filesystem.

    We specifically avoid removing symlinks in the path so that the filepath
    remains under the website root. Also, we don't want trailing slashes for
    directories.

    """
    parts = [root] + url.lstrip('/').split('/')
    return os.sep.join(parts).rstrip(os.sep)


# WSGIFilter
# ==========

def header_value(headers, name):
    """Yanked from http://svn.pythonpaste.org/Paste/tags/1.3/paste/response.py
    """
    name = name.lower()
    result = [value for header, value in headers
              if header.lower() == name]
    if result:
        return ','.join(result)
    else:
        return None


class WSGIFilter(object):
    """Implement WSGI output-filtering middleware.

    Yanked from (r6574):

      http://svn.pythonpaste.org/Paste/WSGIFilter/trunk/wsgifilter/filter.py

    Docs:

      http://pythonpaste.org/wsgifilter/

    """

    # If this is true, then conditional requests will be diabled
    # (e.g., If-Modified-Since)
    force_no_conditional = True

    conditional_headers = [
        'HTTP_IF_MODIFIED_SINCE',
        'HTTP_IF_NONE_MATCH',
        ]

    # If true, then any status code will be filtered; otherwise only
    # 200 OK responses are filtered
    filter_all_status = False

    # If you provide this (a string or list of string mimetypes) then
    # only content with this mimetype will be filtered
    filter_content_types = ('text/html', )

    # If this is set, then HTTPEncode will be used to decode the value
    # given provided mimetype and this output
    format_output = None

    # You can also use a specific format object, which forces the
    # parsing with that format
    format = None

    # If you aren't using a format but you want unicode instead of
    # 8-bit strings, then set this to true
    decode_unicode = False

    # When we get unicode back from the filter, we'll use this
    # encoding and update the Content-Type:
    output_encoding = 'utf8'

    def __init__(self, app):
        self.app = app
        if isinstance(self.format, basestring):
            from httpencode import get_format
            self.format = get_format(self.format)
        if (self.format is not None
            and self.filter_content_types is Filter.filter_content_types):
            self.filter_content_types = self.format.content_types

    def __call__(self, environ, start_response):
        if self.force_no_conditional:
            for key in self.conditional_headers:
                if key in environ:
                    del environ[key]
        # @@: I should actually figure out a way to deal with some
        # encodings, particular since stuff we don't care about like
        # text/javascript could be gzipped usefully.
        if 'HTTP_ACCEPT_ENCODING' in environ:
            del environ['HTTP_ACCEPT_ENCODING']
        shortcutted = []
        captured = []
        written_output = []
        def replacement_start_response(status, headers, exc_info=None):
            if not self.should_filter(status, headers, exc_info):
                shortcutted.append(None)
                return start_response(status, headers, exc_info)
            if exc_info is not None and shortcutted:
                raise exc_info[0], exc_info[1], exc_info[2]
            # Otherwise we don't care about exc_info...
            captured[:] = [status, headers]
            return written_output.append
        app_iter = self.app(environ, replacement_start_response)
        if shortcutted:
            # We chose not to filter
            return app_iter
        if not captured or written_output:
            # This app hasn't called start_response We can't do
            # anything magic with it; or it used the start_response
            # writer, and we still can't do anything with it
            try:
                for chunk in app_iter:
                    written_output.append(chunk)
            finally:
                if hasattr(app_iter, 'close'):
                    app_iter.close()
            app_iter = written_output
        try:
            return self.filter_output(
                environ, start_response,
                captured[0], captured[1], app_iter)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()

###############################################################################
###
### Irrelevant here
###
###    def paste_deploy_middleware(cls, app, global_conf, **app_conf):
###        # You may wish to override this to make it convert the
###        # arguments or use global_conf.  To declare your entry
###        # point use:
###        # setup(
###        #   entry_points="""
###        #   [paste.filter_app_factory]
###        #   myfilter = myfilter:MyFilter.paste_deploy_middleware
###        #   """)
###        return cls(app, **app_conf)
###
###    paste_deploy_middleware = classmethod(paste_deploy_middleware)
###
###############################################################################

    def should_filter(self, status, headers, exc_info):
        if not self.filter_all_status:
            if not status.startswith('200'):
                return False
        content_type = header_value(headers, 'content-type')
        if content_type and ';' in content_type:
            content_type = content_type.split(';', 1)[0]
        if content_type in self.filter_content_types:
            return True
        return False

    _charset_re = re.compile(
        r'charset="?([a-z0-9-_.]+)"?', re.I)

    # @@: I should do something with these:
    #_meta_equiv_type_re = re.compile(
    #    r'<meta[^>]+http-equiv="?content-type"[^>]*>', re.I)
    #_meta_equiv_value_re = re.compile(
    #    r'value="?[^">]*"?', re.I)

    def filter_output(self, environ, start_response,
                      status, headers, app_iter):
        content_type = header_value(headers, 'content-type')
        if ';' in content_type:
            content_type = content_type.split(';', 1)[0]
        if self.format_output:
            import httpencode
            format = httpencode.registry.find_format_match(self.format_output, content_type)
        else:
            format = self.format
        if format:
            data = format.parse_wsgi_response(status, headers, app_iter)
        else:
            data = ''.join(app_iter)
            if self.decode_unicode:
                # @@: Need to calculate encoding properly
                full_ct = header_value(headers, 'content-type') or ''
                match = self._charset_re.search(full_ct)
                if match:
                    encoding = match.group(0)
                else:
                    # @@: Obviously not a great guess
                    encoding = 'utf8'
                data = data.decode(encoding, 'replace')
        new_output = self.filter(
            environ, headers, data)
        if format:
            app = format.responder(new_output, headers=headers)
            app_iter = app(environ, start_response)
            return app_iter
        else:
            enc_data = []
            encoding = self.output_encoding
            if not isinstance(new_output, basestring):
                for chunk in new_output:
                    if isinstance(chunk, unicode):
                        chunk = chunk.encode(encoding)
                    enc_data.append(chunk)
            elif isinstance(new_output, unicode):
                enc_data.append(new_output.encode(encoding))
            else:
                enc_data.append(new_output)
            start_response(status, headers)
            return enc_data

    def filter(self, environ, headers, data):
        raise NotImplementedError


# Nice Things
# ===========

# Date/Time Helpers
# =================

months = {  1:'January'
         ,  2:'February'
         ,  3:'March'
         ,  4:'April'
         ,  5:'May'
         ,  6:'June'
         ,  7:'July'
         ,  8:'August'
         ,  9:'September'
         , 10:'October'
         , 11:'November'
         , 12:'December'
          }


def ts2age(first, second=None):
    """Given a Unix timestamp or a datetime object, return an age string.

        =========================================== =============== ==========
        range                                       denomination    example
        =========================================== =============== ==========
        0-1 second                                  "just a moment"
        1-59 seconds                                seconds         13 seconds
        60 sec - 59 min                             minutes         13 minutes
        60 min - 23 hrs, 59 min                     hours           13 hours
        24 hrs - 13 days, 23 hrs, 59 min            days            13 days
        14 days - 27 days, 23 hrs, 59 min           weeks           3 weeks
        28 days - 12 months, 31 days, 23 hrs, 59 mn months          6 months
        1 year -                                    years           1 year
        =========================================== =============== ==========

    We'll go up to years for now.

    """

    def convert(timestamp):
        if isinstance(timestamp, datetime.datetime):
            return time.mktime(timestamp.timetuple())
        return timestamp

    first = convert(first)
    if second is None:
        second = time.time()
    else:
        second = convert(second)


    # Define some helpful constants.
    # ==============================

    sec =   1
    min =  60 * sec
    hr  =  60 * min
    day =  24 * hr
    wk  =   7 * day
    mn  =   4 * wk
    yr  = 365 * day


    # Get the raw age in seconds.
    # ===========================

    age = second - first 


    # Convert it to a string.
    # =======================
    # We start with the coarsest unit and filter to the finest. Pluralization is
    # centralized.

    if age < 1:
        return 'just a moment'

    elif age >= yr:         # years
        amount = age / yr
        unit = 'year'
    elif age >= mn:         # months
        amount = age / mn
        unit = 'month'
    elif age >= (2 * wk):   # weeks
        amount = age / wk
        unit = 'week'
    elif age >= day:        # days
        amount = age / day
        unit = 'day'
    elif age >= hr:         # hours
        amount = age / hr
        unit = 'hour'
    elif age >= min:        # minutes
        amount = age / min
        unit = 'minute'
    else:                   # seconds
        amount = age
        unit = 'second'


    # Pluralize and return.
    # =====================

    amount = int(math.floor(amount))
    if amount != 1:
        unit += 's'
    age = ' '.join([str(amount), unit])
    return age

dt2age = ts2age



def format_date(dt, timeonly=False):
    """Given a datetime.datetime obj, return a formatted string.

    If timeonly is set, then don't include the date in the string.

    """
    s = timeonly and "%I:%M %p" or "%B %d, %Y at %I:%M %p"
    s = dt.strftime(s)
    s = s.lstrip('0')
    s = s.replace(' 0', ' ')
    s = s.replace('.0', '.')
    return s


# http://code.djangoproject.com/svn/django/tags/releases/1.0.2/django/forms/fields.py
email_re = re.compile(
 r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
 r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' # quoted-string
 r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain


# States, Territories, Provinces
# ==============================

class OrderableDict(dict):
    __module__ == 'nest.util'
    def ordered(self):
        return sorted(self.values())


states = OrderableDict()
states['AL'] = ('Alabama', 'AL')
states['AK'] = ('Alaska', 'AK')
states['AZ'] = ('Arizona', 'AZ')
states['AR'] = ('Arkansas', 'AR')
states['CA'] = ('California', 'CA')
states['CO'] = ('Colorado', 'CO')
states['CT'] = ('Connecticut', 'CT')
states['DE'] = ('Delaware', 'DE')
states['FL'] = ('Florida', 'FL')
states['GA'] = ('Georgia', 'GA')
states['HI'] = ('Hawaii', 'HI')
states['IA'] = ('Iowa', 'IA')
states['ID'] = ('Idaho', 'ID')
states['IL'] = ('Illinois', 'IL')
states['IN'] = ('Indiana', 'IN')
states['KS'] = ('Kansas', 'KS')
states['KY'] = ('Kentucky', 'KY')
states['LA'] = ('Louisiana', 'LA')
states['MA'] = ('Massachusetts', 'MA')
states['MD'] = ('Maryland', 'MD')
states['ME'] = ('Maine', 'ME')
states['MI'] = ('Michigan', 'MI')
states['MN'] = ('Minnesota', 'MN')
states['MO'] = ('Missouri', 'MO')
states['MS'] = ('Mississippi', 'MS')
states['MT'] = ('Montana', 'MT')
states['NC'] = ('North Carolina', 'NC')
states['ND'] = ('North Dakota', 'ND')
states['NE'] = ('Nebraska', 'NE')
states['NH'] = ('New Hampshire', 'NH')
states['NJ'] = ('New Jersey', 'NJ')
states['NM'] = ('New Mexico', 'NM')
states['NY'] = ('New York', 'NY')
states['NV'] = ('Nevada', 'NV')
states['OH'] = ('Ohio', 'OH')
states['OK'] = ('Oklahoma', 'OK')
states['OR'] = ('Oregon', 'OR')
states['PA'] = ('Pennsylvania', 'PA')
states['RI'] = ('Rhode Island', 'RI')
states['SC'] = ('South Carolina', 'SC')
states['SD'] = ('South Dakota', 'SD')
states['TN'] = ('Tennessee', 'TN')
states['TX'] = ('Texas', 'TX')
states['UT'] = ('Utah', 'UT')
states['VA'] = ('Virginia', 'VA')
states['VE'] = ('Vermont', 'VE')
states['WA'] = ('Washington', 'WA')
states['WI'] = ('Wisconsin', 'WI')
states['WV'] = ('West Virginia', 'WV')
states['WY'] = ('Wyoming', 'WY')

territories = OrderableDict()
territories['PW'] = ('Palau', 'PW')
territories['VI'] = ('Virgin Islands', 'VI')
territories['PR'] = ('Puerto Rico', 'PR')
territories['MP'] = ('Mariana Islands', 'MP')
territories['MH'] = ('Marshall Islands', 'MH')
territories['DC'] = ('District of Columbia', 'DC')
territories['FM'] = ('Micronesia', 'FM')
territories['GU'] = ('Guam', 'GU')
territories['AS'] = ('American Samoa', 'AS')

states_and_territories = OrderableDict()
states_and_territories.update(states)
states_and_territories.update(territories)

provinces = OrderableDict()
provinces['AB'] = ('Alberta', 'AB')
provinces['BC'] = ('British Columbia', 'BC')
provinces['MB'] = ('Manitoba', 'MB')
provinces['NB'] = ('New Brunswick', 'NB')
provinces['NL'] = ('Newfoundland', 'NL')
provinces['NT'] = ('Northwest Territories', 'NT')
provinces['NS'] = ('Nova Scotia', 'NS')
provinces['NU'] = ('Nunavut', 'NU')
provinces['ON'] = ('Ontario', 'ON')
provinces['PE'] = ('Prince Edward Island', 'PE')
provinces['QC'] = ('Quebec', 'QC')
provinces['SK'] = ('Saskatchewan', 'SK')
provinces['YT'] = ('Yukon', 'YT')

states_and_territories_and_provinces = OrderableDict()
states_and_territories_and_provinces.update(states)
states_and_territories_and_provinces.update(territories)
states_and_territories_and_provinces.update(provinces)


# Helpers for listings
# ====================

def columnize(items, numcols=3):
    """Given a sequence, return a None-padded 2D array, sorted down.

    [foo, bar, baz, buz, blee, bloo, blah, blam]

        <becomes>

    [[foo, buz, blah]
     [bar, blee, blam
     [baz, bloo, None]]

    """
    out = []
    offset = int(math.ceil(len(items)/float(numcols)))
    for i in range(0, offset):
        row = []
        for j in range(i, i+(offset*numcols), offset):
            cell = None
            if j < len(items):
                cell = items[j]
            row.append(cell)
        out.append(row)
    return out


def even_odd(sequence):
    """Given a sequence, yield objects wrapped with even/odd info.
    """
    i = 0 
    for obj in sequence:
        is_odd = bool(i % 2)
        is_even = not is_odd
        yield { 'is_even':is_even
              , 'is_odd':is_odd
              , 'even_odd':is_even and 'even' or 'odd'
              , 'obj':obj
               }
        i += 1



# Test
# ====

if __name__ == '__main__':
    import doctest
    doctest.testmod()
