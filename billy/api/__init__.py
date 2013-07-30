from __future__ import unicode_literals
import re

import difflib
from flask import request
from flask.ext.restful import Api
from flask.ext.restful.utils import unauthorized, error_data
from flask.signals import got_request_exception
from werkzeug.http import HTTP_STATUS_CODES
from werkzeug.exceptions import HTTPException


class ApiFixed(Api):

    def handle_error(self, e):
            """Error handler for the API transforms a raised exception into a Flask
            response, with the appropriate HTTP status code and body.

            :param e: the raised Exception object
            :type e: Exception

            """
            got_request_exception.send(self.app, exception=e)
            if isinstance(e, HTTPException):
                return e
            code = getattr(e, 'code', 500)
            data = getattr(e, 'data', error_data(code))

            if code >= 500:
                self.app.logger.exception("Internal Error")

            if code == 404 and ('message' not in data or
                                data['message'] == HTTP_STATUS_CODES[404]):
                rules = dict([(re.sub('(<.*>)', '', rule.rule), rule.rule)
                              for rule in self.app.url_map.iter_rules()])
                close_matches = difflib.get_close_matches(
                    request.path, rules.keys())
                if close_matches:
                    # If we already have a message, add punctuation and
                    # continue it.
                    if "message" in data:
                        data["message"] += ". "
                    else:
                        data["message"] = ""

                    data['message'] += 'You have requested this URI [' + request.path + \
                        '] but did you mean ' + \
                        ' or '.join((rules[match]
                        for match in close_matches)) + ' ?'

            resp = self.make_response(data, code)

            if code == 401:
                resp = unauthorized(resp,
                                    self.app.config.get("HTTP_BASIC_AUTH_REALM", "flask-restful"))

            return resp
