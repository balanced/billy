from __future__ import unicode_literals

from pyramid.httpexceptions import HTTPBadRequest

from .auth import auth_api_key


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
    # Notice: this make validators can query to database
    form.session = request.session
    validation_result = form.validate()
    if not validation_result:
        raise form_errors_to_bad_request(form.errors)
    return form


class RecordExistValidator(object):
    """This validator make sure there is a record exists for a given GUID

    """

    def __init__(self, model_cls):
        self.model_cls = model_cls

    def __call__(self, form, field):
        # Notice: we should set form.session before we call validate
        model = self.model_cls(form.session)
        if model.get(field.data) is None:
            msg = field.gettext('No such {} record {}'
                                .format(self.model_cls.TABLE.__name__, 
                                        field.data))
            raise ValueError(msg)


def list_by_company_guid(request, model_cls):
    """List records by company guid

    """
    company = auth_api_key(request)
    model = model_cls(request.session)
    offset = int(request.params.get('offset', 0))
    limit = int(request.params.get('limit', 20))
    items = model.list_by_company_guid(
        company_guid=company.guid,
        offset=offset,
        limit=limit,
    )
    result = dict(
        items=list(items),
        offset=offset,
        limit=limit,
    )
    return result
