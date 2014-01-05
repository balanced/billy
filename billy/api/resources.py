from __future__ import unicode_literals

from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.httpexceptions import HTTPNotFound


class IndexResource(object):
    __acl__ = [
        #       principal      action
        (Allow, Authenticated, 'view'),
        (Allow, Authenticated, 'create'),
    ]

    #: the class of model
    MODEL_CLS = None

    #: entity name
    ENTITY_NAME = None

    #: entity resource
    ENTITY_RESOURCE = None

    def __init__(self, request, parent=None, name=None):
        self.__name__ = name
        self.__parent__ = parent
        self.request = request
        assert self.MODEL_CLS is not None
        assert self.ENTITY_NAME is not None
        assert self.ENTITY_RESOURCE is not None

    def __getitem__(self, key):
        model = self.MODEL_CLS(self.request.model_factory)
        entity = model.get(key)
        if entity is None:
            raise HTTPNotFound('No such {} {}'.format(self.ENTITY_NAME, key))
        return self.ENTITY_RESOURCE(self.request, entity, parent=self, name=key)


class EntityResource(object):

    def __init__(self, request, entity, parent=None, name=None):
        self.__name__ = name
        self.__parent__ = parent
        self.request = request
        self.entity = entity
        # make sure only the owner company can access the entity
        company_principal = 'company:{}'.format(self.company.guid)
        self.__acl__ = [
            #       principal          action
            (Allow, company_principal, 'view'),
        ]

    @property
    def company(self):
        raise NotImplemented()
