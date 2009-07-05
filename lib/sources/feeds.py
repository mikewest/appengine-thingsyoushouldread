# -*- coding: utf-8 -*-

# Time processing
import rfc822
from   datetime import datetime

# Feed acquisition and processing
from google.appengine.ext import db
from google.appengine.api import urlfetch
from xml.etree.cElementTree import fromstring

""" Base class that pulls in an atom-compliant feed, and extracts
    the basic bookmarking information that's relevant to this app"""
class AtomFeed( object ):
    def __init__( self, url, category ):
        self.url        =   url
        self.category   =   category
        self.links      =   []

    def _pull_feed( self ):
        response = urlfetch.fetch( self.url )
        if response.status_code == 200:
            xml     = fromstring( response.content )
            for element in xml.findall( 'channel/item' ):
                link    =   {
                                'guid':             element.find('guid').text,
                                'title':            element.find('title').text,
                                'url':              element.find('link').text,
                                'description':      element.find('description').text,
                                'published':        element.find('pubDate').text,
                                'category':         self.category,
                                'starred':          self.category == u'Starred',
                            }
                self.links.append( link )

    def _normalize_rfc822_date( self, date_string ):
        return  datetime.fromtimestamp(
                    rfc822.mktime_tz(
                        rfc822.parsedate_tz(
                            date_string
                        )
                    )
                )

    def update( self ):
        self._pull_feed()
        self._postprocess_feed()

"""InstapaperFeed subclasses AtomFeed for most of it's functionality"""
class InstapaperFeed( AtomFeed ):
    def _postprocess_feed( self ):
        for link in self.links:
            link['key_name']    =   u'instapaper::%s' % link['guid']
            link['published']   =   self._normalize_rfc822_date(
                                        link['published']
                                    )
