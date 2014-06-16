from __future__ import unicode_literals


def allow_origin_tween_factory(handler, registry):
    """Allow cross origin XHR requests

    """
    def allow_origin_tween(request):
        request_origin = request.headers.get('origin')

        def is_origin_allowed(origin):
            allowed_origins = (
                request.registry.settings.get('api.allowed_origins', [])
            )
            if not origin:
                return False
            for allowed_origin in allowed_origins:
                if origin.lower().startswith(allowed_origin):
                    return True
            return False

        def allow_origin_callback(request, response):
            """Set access-control-allow-origin et. al headers

            """
            response.headers[b'Access-Control-Allow-Origin'] = request_origin
            response.headers[b'Access-Control-Allow-Credentials'] = b'true'
            response.headers[b'Access-Control-Allow-Methods'] = (
                b'GET, POST, PUT, DELETE, PATCH, OPTIONS'
            )
            response.headers[b'Access-Control-Allow-Headers'] = (
                b'Content-Type,Authorization'
            )

        if not is_origin_allowed(request_origin):
            return handler(request)

        request.add_response_callback(allow_origin_callback)
        return handler(request)
    return allow_origin_tween
