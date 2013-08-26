from __future__ import unicode_literals

from pyramid.httpexceptions import HTTPBadRequest


def form_errors_to_bad_request(errors):
    """Convert WTForm errors into readable bad request

    """
    error_params = []
    error_params.append('<ul>')
    for param_key, param_errors in errors.iteritems():
        indent = ' ' * 4
        error_params.append(indent + '<li>')
        indent = ' ' * 8
        error_params.append(indent + '{}:<ul>'.format(param_key))
        for param_error in param_errors:
            indent = ' ' * 12
            error_params.append(indent + '<li>{}</li>'.format(param_error))
        indent = ' ' * 8
        error_params.append(indent + '</ul>')
        indent = ' ' * 4
        error_params.append(indent + '</li>')
    error_params.append('</ul>')
    error_params = '\n'.join(error_params)
    message = "There are errors in following parameters: {}".format(error_params)
    return HTTPBadRequest(message)


def validate_form(form_cls, request):
    """Validate form and raise exception if necessary

    """
    form = form_cls(request.params)
    validation_result = form.validate()
    if not validation_result:
        raise form_errors_to_bad_request(form.errors)
    return form
