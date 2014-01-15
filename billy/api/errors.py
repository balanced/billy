from __future__ import unicode_literals

from pyramid.view import view_config
from pyramid.renderers import render_to_response
from pyramid.security import NO_PERMISSION_REQUIRED

from billy.errors import BillyError
from billy.models.subscription import SubscriptionCanceledError
from billy.models.invoice import InvalidOperationError
from billy.models.invoice import DuplicateExternalIDError
from billy.models.processors.balanced_payments import InvalidURIFormat

#: the default error status code
DEFAULT_ERROR_STATUS_CODE = 400
#: mapping from error class to status code
ERROR_STATUS_MAP = {
    SubscriptionCanceledError: 400,
    InvalidOperationError: 400,
    DuplicateExternalIDError: 409,
    InvalidURIFormat: 400,
}


def error_response(request, error, status):
    """Create an error response from given error

    """
    response = render_to_response(
        renderer_name='json',
        value=dict(
            error_class=error.__class__.__name__,
            error_message=error.msg,
        ),
        request=request,
    )
    response.status = status
    return response


@view_config(
    context=BillyError,
    permission=NO_PERMISSION_REQUIRED,
)
def display_error(error, request):
    cls = type(error)
    status = ERROR_STATUS_MAP.get(cls, DEFAULT_ERROR_STATUS_CODE)
    return error_response(request, error, status)
