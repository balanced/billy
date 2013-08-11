from __future__ import unicode_literals
import os

DEBUG_MODE = os.environ.get('DEBUG_MODE', 'PROD')
DEBUG = True if DEBUG_MODE.lower() == 'dev' else False


from .all import *
if DEBUG:
    from .debug import *
else:
    from .prod import *
