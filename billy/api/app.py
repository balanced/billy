from __future__ import unicode_literals

from flask import Flask

from api.spec import billy_spec
from api.resources.base import Home
from api import ApiFixed

app = Flask(__name__)
api = ApiFixed(app)

api.add_resource(Home, '/')
# Register the resources using the spec
for resource, data in billy_spec.iteritems():
    api.add_resource(data['controller'], data['path'])
