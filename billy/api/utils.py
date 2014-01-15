from __future__ import unicode_literals
import re

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.path import DottedNameResolver

# the minimum amount in a transaction
MINIMUM_AMOUNT = 50

# regular expression for appears_on_statement_as field
# this basically accepts
#    ASCII letters (a-z and A-Z)
#    Digits (0-9)
#    Special characters (.<>(){}[]+&!$;-%_?:#@~='" ^\`|)
STATEMENT_REXP = (
    '^[0-9a-zA-Z{}]*$'.format(re.escape('''.<>(){}[]+&!$;-%_?:#@~='" ^\`|'''))
)


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
    form.model_factory = request.model_factory
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
        # Notice: we should set form.model_factory before we call validate
        model = self.model_cls(form.model_factory)
        if model.get(field.data) is None:
            msg = field.gettext('No such {} record {}'
                                .format(self.model_cls.TABLE.__name__,
                                        field.data))
            raise ValueError(msg)


def list_by_context(request, model_cls, context):
    """List records by a given context

    """
    model = model_cls(request.model_factory)
    offset = int(request.params.get('offset', 0))
    limit = int(request.params.get('limit', 20))
    kwargs = {}
    if 'external_id' in request.params:
        kwargs['external_id'] = request.params['external_id']
    if 'processor_uri' in request.params:
        kwargs['processor_uri'] = request.params['processor_uri']
    items = model.list_by_context(
        context=context,
        offset=offset,
        limit=limit,
        **kwargs
    )
    result = dict(
        items=list(items),
        offset=offset,
        limit=limit,
    )
    return result


def get_processor_factory(settings):
    """Get processor factory from settings and return

    """
    resolver = DottedNameResolver()
    processor_factory = settings['billy.processor_factory']
    processor_factory = resolver.maybe_resolve(processor_factory)
    return processor_factory
