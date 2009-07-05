# -*- coding: utf-8 -*-

from google.appengine.ext import db

class Bookmark( db.Model ):
    url         =  db.LinkProperty()
    title       =  db.StringProperty()
    description =  db.TextProperty()
    category    =  db.StringProperty()
    published   =  db.DateTimeProperty()
