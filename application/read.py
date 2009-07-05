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
from google.appengine.api.labs import taskqueue

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

class ListView( EasyRenderingRequestHandler ):
    def get( self, folder ):
        links = db.GqlQuery( 'SELECT * FROM Bookmark WHERE category = :1 ORDER BY published DESC', folder );
        self.renderHtml( 'listview.html', { 'links': links, 'folder': folder.lower() } )


#
# Workers
#
class WorkerBase( webapp.RequestHandler ):
    def get( self ):
        if self._process():
            self.response.out.write('SUCCESS');
        else:
            self.error( 500 )

class FeedWorker( WorkerBase ):
    def _process( self ):
        """Process a feed; requires `url` and `category`"""
        self.url        = self.request.get('url')
        self.category   = self.request.get('category')
        feed            = False
        if self.url.startswith( 'http://www.instapaper.com' ):
            feed = InstapaperFeed( url=self.url, category=self.category )
        
        if feed:
            feed.update()
            for link in feed.links:
                taskqueue.add( url='/task/item/', params=link )
            return true
        else:
            return false

class ItemWorker( WorkerBase ):
    def _process( self ):
        """Process an item, fed in as a few POST params"""
        self.key_name = self.response.get('key_name')
        if self.key_name:
            db.run_in_transaction( self._item_txn )

    def _item_txn( self ):
        link = Bookmark.get_by_key_name( self.key_name )
        if link is None:
            link    =   Bookmark(
                            key_name=self.key_name,
                            title=self.response.get('title'),
                            url=db.Link(self.response.get('url')),
                            description=self.response.get('description'),
                            published=self.response.get('published'),
                            category=self.response.get('category'),
                            normalized_url=False,
                            starred=self.response.get('starred')
                        )
            link.put()
        else:
            if self.response.get('category') == u'Starred':
                if not link.starred:
                    link.starred = True
                    link.put()
            elif self.response.get('category') != link.category:
                link.category = self.response.get('category')
                link.put()
#
# Cron
#
class UpdateInstapaper( webapp.RequestHandler ):
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
                            ),
                            (
                                u'Starred',
                                u'http://www.instapaper.com/starred/rss/203164/fvc7FjLu4aIN5wsniOahrlWgbLw'
                            )
                        ]
        for category, url in feedlist:
            taskqueue.add( url='/task/feed/', params={ 'url': url, 'category': category } )
        self.response.clear()
        self.response.set_status( 202 ) # 202 = Accepted

class NotFound( EasyRenderingRequestHandler ):
    def get( self ):
        self.renderHtml( '404.html', {} )

def main():
    ROUTES = [
        ( '/',              Index ),
        ( '/folder/([a-zA-Z\.]*)/', ListView ),
        
        ( '/task/update/',          UpdateInstapaper ),
        ( '/task/feed/',            FeedWorker ),
        ( '/task/item/',            ItemWorker ),

        ( '/rss',           RSS ),
        ( '/*',             NotFound )
    ]
    application = webapp.WSGIApplication( ROUTES, debug=DEBUG )
    run_wsgi_app(application)

if __name__ == "__main__":
  main()
