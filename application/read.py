# -*- coding: utf-8 -*-
 
import os, sys, re

sys.path.insert( 0, os.path.join( os.path.dirname( __file__ ), '..' ) )
from etc.settings import APP_BASE, TEMPLATES_BASE, DEBUG

sys.path.insert( 0, os.path.join( APP_BASE, 'models' ) )
sys.path.insert( 0, os.path.join( APP_BASE, 'lib' ) )
sys.path.insert( 0, os.path.join( APP_BASE, 'lib', 'jinja2' ) )

# Import AppEngine stuff
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# Import models and templating
from models.Bookmark import Bookmark
from jinja2 import Environment, FileSystemLoader
 
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
        from xml.etree.cElementTree import fromstring 
        url = 'http://www.instapaper.com/rss/203164/y9GD9Jqfv9rxl5tQrFptls3Pc'
        result = urlfetch.fetch(url)
        if result.status_code == 200:
            rss     = fromstring( result.content )
            links   = []
            self.response.headers['Content-Type'] = 'text/plain'
            for element in rss.findall( 'channel/item' ):
                link = Bookmark(title=element.find('title').text,
                                link=db.Link(element.find('link').text),
                                guid=db.Link(element.find('guid').text),
                                description=element.find('description').text,
                                published=element.find('pubDate').text,
                                category="Unread")
                self.response.out.write(
                    "title: %s\nurl: %s\n" % (
                        element.find('title').text,
                        element.find('link').text
                    )
                )
        else:
            self.renderText( 'index.html', {} )

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
