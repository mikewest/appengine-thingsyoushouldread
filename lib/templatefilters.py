# -*- coding: utf-8 -*-

from google.appengine.ext import webapp
import hashlib

def hash( value ):
    return hashlib.md5( value ).hexdigest()

register = webapp.template.create_template_register()
register.filter(hash)
