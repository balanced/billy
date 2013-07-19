from __future__ import unicode_literals

from flask import Flask
from flask.ext import restful

from settings import DEBUG
from views import *

app = Flask(__name__)
api = restful.Api(app)
api.handle_error = lambda error: error


api.add_resource(Home, '/')
api.add_resource(AuthenticatedView, '/auth/')

if __name__ == '__main__':
    app.debug = DEBUG
    app.run()
