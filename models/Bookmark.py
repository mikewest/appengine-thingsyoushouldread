# -*- coding: utf-8 -*-

from google.appengine.ext import db

class Bookmark( db.Model ):
    url             =  db.LinkProperty()
    normalized_url  =  db.BooleanProperty()
    starred         =  db.BooleanProperty()
    title           =  db.StringProperty()
    description     =  db.TextProperty()
    category        =  db.StringProperty()
    published       =  db.DateTimeProperty()
    tags            =  db.StringListProperty()
