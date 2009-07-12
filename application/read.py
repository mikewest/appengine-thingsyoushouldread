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
from google.appengine.api import memcache
from google.appengine.api.labs.taskqueue import Task
import pickle
import logging

# Import models and templating
from models.Bookmark import Bookmark
from sources.feeds import InstapaperFeed

class EasyRenderingRequestHandler( webapp.RequestHandler ):
    def renderFromMemcache( self, memcache_key ):
        data = memcache.get( memcache_key )
        if data is None:
            return False
        else:
            self.response.headers['Content-Type'] = data[0]
            self.response.out.write( data[1] )
            return True

    def renderText( self, template_filename, context ):
        self.render( 'text/plain/', template_filename, context )

    def renderXML( self, template_filename, context ):
        self.render( 'text/xml', template_filename, context )

    def renderHtml( self, template_filename, context ):
        self.render( 'text/html', template_filename, context )

    def renderFeed( self, template_filename, context ):
        self.render( 'application/atom+xml', template_filename, context )

    def render404( self ):
        self.response.set_status( 404 )
        self.render( 'text/html', '404.html', {} )

    def render( self, content_type, template_filename, context ):
        path = '%s/%s' % ( TEMPLATES_BASE, template_filename )
        if content_type:
            self.response.headers['Content-Type'] = content_type
        html = template.render( path, context )
        if context.has_key( 'memcache_key' ):
            memcache.set( key=context['memcache_key'], value=(content_type, html), time=1800 ) 
        self.response.out.write( template.render( path,  context ) ) 

class Index( EasyRenderingRequestHandler ):
    def get( self ):
        if self.renderFromMemcache( 'index' ):
            return True

        self.renderHtml( 'index.html', { 'memcache_key': 'index' } )

class ListView( EasyRenderingRequestHandler ):
    def get( self, folder ):
        memcache_key = 'list_%s' % folder
        if self.renderFromMemcache( memcache_key ):
            return True

        if folder == 'Starred':
            links = db.GqlQuery( 'SELECT * FROM Bookmark WHERE starred = True ORDER BY published DESC' )
        elif folder == 'Recent':
            links = db.GqlQuery( 'SELECT * FROM Bookmark ORDER BY published DESC LIMIT 25' )
        else:
            links = db.GqlQuery( 'SELECT * FROM Bookmark WHERE category = :1 ORDER BY published DESC', folder )
        if links.count():
            self.renderHtml( 'listview.html', {
                                                'links':        links,
                                                'folder':       folder,
                                                'memcache_key': memcache_key } )
        else:
            self.render404()

class FeedView( EasyRenderingRequestHandler ):
    def get( self, folder ):
        memcache_key = 'feed_%s' % folder
        if self.renderFromMemcache( memcache_key ):
            return True

        if folder == 'Starred':
            links = db.GqlQuery( 'SELECT * FROM Bookmark WHERE starred = True ORDER BY published DESC LIMIT 25' )
        elif folder == 'Recent':
            links = db.GqlQuery( 'SELECT * FROM Bookmark ORDER BY published DESC LIMIT 25' )
        else:
           links = db.GqlQuery( 'SELECT * FROM Bookmark WHERE category = :1 ORDER BY published DESC LIMIT 25', folder )
        if links.count():
            updated = links[ 0 ].published
            self.renderFeed( 'feedview.html', { 'links':        links,
                                                'last_updated': updated,
                                                'folder':       folder,
                                                'memcache_key': memcache_key } )
        else:
            self.render404()
        
#
# Workers
#
class WorkerBase( webapp.RequestHandler ):
    def post( self ):
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
                Task( url='/task/item/', params={ 'link': pickle.dumps(link) } ).add( queue_name='items' )
            return True
        else:
            return False

class ItemWorker( WorkerBase ):
    def _process( self ):
        """Process an item, fed in as a few POST params"""
        self.item = pickle.loads( str( self.request.get( 'link' ) ) )
        if self.item['key_name']:
            db.run_in_transaction( self._item_txn )
            return True
        else:
            return False

    def _normalize_url( self, url ):
        from google.appengine.api import urlfetch
        from google.appengine.api.urlfetch import DownloadError 

        original_url        = url        
        found_final_url     = False
        redirects_remaining = 5
        logging.info( "Normalizing '%s'" % url )
        while not found_final_url and redirects_remaining > 0:
            retry_count = 3
            try:
                response = urlfetch.fetch( url, follow_redirects=False )
            except DownloadError:
                logging.error( "DownloadError thrown while retrieving '%s': Aborting" % url )
                return url

            if response.status_code in [ 301, 302, 303, 307 ]:
                redirects_remaining -= 1
                if response.headers['Location']:
                    url = response.headers['Location']
                else:
                    logging.error( 'Redirect from %s with status %s, but no Location header' % ( url, response.status_code ) )
            else:
                found_final_url = True
        return url

    def _crowdsource_tags( self, url ):
        from google.appengine.api import urlfetch
        from django.utils import simplejson
       
        logging.info( 'Crowdsourcing tags for %s' % url )

        delicious = 'http://feeds.delicious.com/v2/json/urlinfo?url=%s' % url
        response  = urlfetch.fetch( delicious )
        if response.status_code == 200:
            logging.info( 'Response from delicious: {{ %s }}' % response.content )
            data = simplejson.loads( response.content )
            if len( data ) > 0 and data[0].has_key('top_tags'):
                return [ tag for tag in data[0]['top_tags'] ]
            else:
                return []
        else:
            return None


    def _item_txn( self ):
        link = Bookmark.get_by_key_name( self.item['key_name'] )
        if link is None:
            link    =   Bookmark(
                            key_name=self.item['key_name'],
                            title=self.item['title'],
                            url=db.Link(self.item['url']),
                            description=self.item['description'],
                            published=self.item['published'],
                            category=self.item['category'],
                            normalized_url=False,
                            starred=self.item['starred']
                        )
        else:
            if self.item['category'] == u'Starred':
                if not link.starred:
                    link.starred    = True
                    link.published  = self.item['published']
            elif self.item['category'] != link.category:
                link.category   = self.item['category']
                link.published  = self.item['published']  

        if not link.normalized_url:
            normalized = self._normalize_url( link.url )
            if normalized != link.url:
                link.url = normalized
            link.normalized_url = True
       
        if ( link.tags == [] or link.tags is None ) and link.category != u'To Be Read':
            link.tags = self._crowdsource_tags( link.url )

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
        tasks   =   [
                        Task(
                            url='/task/feed/',
                            params={
                                        'url': url,
                                        'category': category
                                    }
                        )
                        for category, url in feedlist
                    ]
        for task in tasks:
            task.add( queue_name="feeds" )
        self.response.clear()
        self.response.set_status( 202 ) # 202 = Accepted

class NotFound( EasyRenderingRequestHandler ):
    def get( self ):
        self.renderHtml( '404.html', {} )

def main():
    ROUTES = [
        ( '/',                          Index ),
        ( '/folder/([a-zA-Z\.]*)/',     ListView ),
        ( '/folder/([a-zA-Z\.]*)/feed/', FeedView ),

        ( '/task/update/',          UpdateInstapaper ),
        ( '/task/feed/',            FeedWorker ),
        ( '/task/item/',            ItemWorker ),

        ( '/*',                     NotFound )
    ]
    application = webapp.WSGIApplication( ROUTES, debug=DEBUG )
    webapp.template.register_template_library('lib.templatefilters')
    run_wsgi_app(application)

if __name__ == "__main__":
  main()
