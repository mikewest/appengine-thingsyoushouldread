# -*- coding: utf-8 -*-
 
import os, sys, re
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

sys.path.insert( 0, os.path.join( os.path.dirname( __file__ ), '..' ) )
from etc.settings import APP_BASE, TEMPLATES_BASE, DEBUG
 
sys.path.insert( 0, os.path.join( APP_BASE, 'lib' ) )
sys.path.insert( 0, os.path.join( APP_BASE, 'lib', 'jinja2' ) )
from jinja2   import Environment, FileSystemLoader
 
env = Environment( loader=FileSystemLoader( TEMPLATES_BASE ) )

class EasyRenderingRequestHandler( webapp.RequestHandler ):
    def renderText( self, template_filename, context ):
        self.response.headers['Content-Type'] = 'text/plain'
        self.render( template_filename, context )

    def renderXML( self, template_filename, context ):
        self.response.headers['Content-Type'] = 'text/xml'
        self.render( template_filename, context )

    def renderHtml( self, template_filename, context ):
        self.response.headers['Content-Type'] = 'text/html'
        self.render( template_filename, context )

    def render( self, template_filename, context ):
        template = env.get_template( template_filename )
        self.response.out.write( template.render( context ) ) 

class Index( EasyRenderingRequestHandler ):
    def get( self ):
        self.renderHtml( 'index.html', {} )

class RSS( EasyRenderingRequestHandler ):
    def get( self ):
        # http://www.instapaper.com/rss/203164/y9GD9Jqfv9rxl5tQrFptls3Pc
        from google.appengine.api import urlfetch

        url = 'http://www.instapaper.com/rss/203164/y9GD9Jqfv9rxl5tQrFptls3Pc'
        result = urlfetch.fetch(url)
#        if result.status_code == 200:
#            self.renderXML(
#                'rss.html',
#                {
#                    'name':     'Read Later',
#                    'content':  result.content
#                }
#            ) 
#        else:
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write( result.status_code )
        self.response.out.write( 'Content: "'+result.content+'"' )

class NotFound( EasyRenderingRequestHandler ):
    def get( self ):
        self.renderHtml( '404.html', {} )

def main():
    ROUTES = [
        ( '/',  Index ),
        ( '/rss', RSS ),
        ( '/*', NotFound )
    ]
    application = webapp.WSGIApplication( ROUTES, debug=DEBUG )
    run_wsgi_app(application)

if __name__ == "__main__":
  main()
