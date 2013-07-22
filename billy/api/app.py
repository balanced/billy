from __future__ import unicode_literals

from flask import Flask
from flask.ext import restful

from billy.settings import DEBUG
from billy.api.resources import *

app = Flask(__name__)
api = restful.Api(app)
api.handle_error = lambda error: error


api.add_resource(Home, '/')
api.add_resource(GroupView, '/auth/')

if __name__ == '__main__':
    app.debug = DEBUG
    app.run()
