# -*- coding: utf-8 -*-
 
import os, sys, re

sys.path.insert( 0, os.path.join( os.path.dirname( __file__ ), '..' ) )
from etc.settings import APP_BASE, TEMPLATES_BASE, DEBUG

sys.path.insert( 0, os.path.join( APP_BASE, 'models' ) )
sys.path.insert( 0, os.path.join( APP_BASE, 'lib' ) )
sys.path.insert( 0, os.path.join( APP_BASE, 'lib', 'sources' ) )

# Import AppEngine stuff
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# Import models and templating
from models.Bookmark import Bookmark
from sources.feeds import InstapaperFeed

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
        path = '%s/%s' % ( TEMPLATES_BASE, template_filename )

        self.response.out.write( template.render( path,  context ) ) 

class Index( EasyRenderingRequestHandler ):
    def get( self ):
        self.renderHtml( 'index.html', {} )

class RSS( EasyRenderingRequestHandler ):
    def get( self ):
        feedlist    =   [
                            (
                                u'Writing',
                                u'http://www.instapaper.com/folder/7134/rss/203164/fvc7FjLu4aIN5wsniOahrlWgbLw'
                            ),
                            (
                                u'Programming',
                                u'http://www.instapaper.com/folder/1383/rss/203164/fvc7FjLu4aIN5wsniOahrlWgbLw',
                            ),
                            (
                                u'Tech',
                                u'http://www.instapaper.com/folder/1384/rss/203164/fvc7FjLu4aIN5wsniOahrlWgbLw'
                            ),
                            (
                                u'Politics',
                                u'http://www.instapaper.com/folder/1386/rss/203164/fvc7FjLu4aIN5wsniOahrlWgbLw'
                            ),
                            (
                                u'Etc.',
                                u'http://www.instapaper.com/folder/6485/rss/203164/fvc7FjLu4aIN5wsniOahrlWgbLw'
                            ),
                            (
                                u'Design',
                                u'http://www.instapaper.com/folder/6491/rss/203164/fvc7FjLu4aIN5wsniOahrlWgbLw'
                            ),
                            (
                                u'To Be Read',
                                u'http://www.instapaper.com/rss/203164/y9GD9Jqfv9rxl5tQrFptls3Pc'
                            )
                        ]
        feeds       =   [ InstapaperFeed( url=url, category=category ) for category, url in feedlist ]
        
        for feed in feeds:
            feed.update( Bookmark )

        self.redirect('/')

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
