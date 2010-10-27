import logging
import os
import sys

import aspen
import webob
from aspen import mode
from aspen.handlers import autoindex, simplates
from aspen.exceptions import HandlerError
from aspen.utils import check_trailing_slash, find_default, translate
from jinja2 import Environment, FileSystemLoader


log = logging.getLogger('aspen.website')


class Website(object):
    """Represent a website.
    """

    def __init__(self, server):
        self.server = server
        self.configuration = server.configuration
        self.root = self.configuration.paths.root


    # Main Dispatcher
    # ===============

    def __call__(self, environ, start_response):
        """Main WSGI callable.
        """

        request = webob.Request(environ)


        # Translate the request to the filesystem.
        # ========================================

        def http404():
            start_response('404 Not Found', [])
            return ['Resource not found.']
        
        hide = False
        fspath = translate(self.root, environ['PATH_INFO'])
        if self.configuration.paths.__ is not None:
            if fspath.startswith(self.configuration.paths.__):  # magic dir
                hide = True
        if hide:
            return http404()
        environ['PATH_TRANSLATED'] = fspath
        fspath = find_default(self.configuration.defaults, fspath)
        if os.path.isdir(fspath):
            return autoindex.wsgi(environ, start_response)
        response = check_trailing_slash(environ, start_response)
        if response is not None: # redirect
            return response
        if not os.path.isfile(fspath):
            return http404()


        # Load a simplate.
        # ================

        simplate = simplates.load(fspath)
        mimetype, namespace, script, template = simplate
       
    
        # Get a response.
        # ===============
    
        if namespace is None:
            log.debug('serving as a static file (not a simplate)')
            response = webob.Response(template)
        else:
            log.debug('serving as a simplate (not a static file)')
            response = webob.Response()
            response.content_type = '' # we set this later if still empty
    
           
            # Add auth abstractions to request.
            # =================================
    
            #log.debug('adding auth abstractions')
            #user = None
            #key = request.cookies.get('key')
            #if key is not None:
            #    log.debug('authenticating user %s' % key)
            #    user = nest.db.users.find_one({'key':key})
            #request.user = user
    
    
            # Populate namespace.
            # ===================
        
            namespace['request'] = request
            namespace['response'] = response
       
    
            # Exec the script.
            # ================
        
            log.debug('executing the script')
            if script:
                try:
                    exec script in namespace
                except SystemExit, exc:
                    if len(exc.args) > 0:
                        response = exc.args[0]
        
        
            # Process the template.
            # =====================
            # If template is None that means that that section was empty.
        
            if template is not None:
                log.debug('processing the template')
                tpl = os.path.join(aspen.paths.root, '__', 'tpl')
                loader = FileSystemLoader([tpl])
                template.environment.loader = loader
                if aspen.mode.STPROD:
                    response.app_iter = template.generate(namespace)
                else:
                    # errors break chunked encoding with generator?
                    response.unicode_body = template.render(namespace)


        # Set the mimetype.
        # =================
        # Note that we guess based on the filesystem path, not the URL path.
        
        if response.content_type == '':
            log.debug('setting the mimetype')
            if mimetype.startswith('text/'):
                mimetype += "; charset=UTF-8"
            if 'Content-Type' in response.headers:
                del response.headers['Content-Type']
            response.headers['Content-Type'] = mimetype
            log.debug('mimetype set to %s' % mimetype)
 

        # Return.
        # =======
    
        log.debug('made it!')
        log.debug('')
        out = response(environ, start_response)
        import pdb; pdb.set_trace()
        return out
