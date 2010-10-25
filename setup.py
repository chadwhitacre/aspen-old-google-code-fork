from setuptools import find_packages, setup


classifiers = [
    'Development Status :: 5 - Production/Stable'
  , 'Environment :: Console'
  , 'Intended Audience :: Developers'
  , 'License :: OSI Approved :: MIT License'
  , 'Natural Language :: English'
  , 'Operating System :: MacOS :: MacOS X'
  , 'Operating System :: Microsoft :: Windows'
  , 'Operating System :: POSIX'
  , 'Programming Language :: Python'
  , 'Topic :: Internet :: WWW/HTTP :: HTTP Servers'
  , 'Topic :: Internet :: WWW/HTTP :: WSGI'
  , 'Topic :: Internet :: WWW/HTTP :: WSGI :: Application'
  , 'Topic :: Internet :: WWW/HTTP :: WSGI :: Server'
   ]

setup( name = 'aspen'
     , version = '~~VERSION~~'
     , packages = find_packages('.') 
     , scripts = ['bin/aspen', 'bin/aspen.mod_wsgi']
     , description = 'Aspen is a highly extensible Python webserver.'
     , author = 'Chad Whitacre'
     , author_email = 'chad@zetaweb.com'
     , url = 'http://aspen.io/'
     , classifiers = classifiers
     , install_requires=[
        'webob == 1.0',
        'jinja2 == 2.5.5'
    ],
)
