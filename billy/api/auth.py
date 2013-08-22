from pyramid.httpexceptions import HTTPForbidden

from billy.models.company import CompanyModel


def auth_api_key(request):
    """Authenticate API KEY and return corresponding company

    """
    model = CompanyModel(request.session)
    company = model.get_by_api_key(request.remote_user)
    if company is None:
        raise HTTPForbidden('Invalid API key {}'.format(request.remote_user))
    return company
