from __future__ import unicode_literals

from sqlalchemy import Unicode, Column, Enum, Boolean
from sqlalchemy.orm import relationship

from models import Base
from processor import processor_map
from utils.generic import api_key_factory, uuid_factory


class Group(Base):
    __tablename__ = 'groups'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('GR'))
    external_id = Column(Unicode, unique=True)
    api_key = Column(Unicode, unique=True, default=api_key_factory())
    provider = Column(Enum(*processor_map.keys(), name='provider_enum'),
                      nullable=False)
    provider_api_key = Column(Unicode, nullable=False)
    is_test = Column(Boolean, default=True)

    coupons = relationship('Coupon', backref='group', cascade='delete')
    customers = relationship('Customer', backref='group', cascade='delete')
    plans = relationship('Plan', backref='group', lazy='dynamic',
                         cascade='delete')
    payouts = relationship('Payout', backref='group', lazy='dynamic',
                           cascade='delete')

    @classmethod
    def create(cls, external_id, provider, provider_api_key, is_test=True,
               **kwargs):
        new_group = cls(external_id=external_id, provider=provider,
                        provider_api_key=provider_api_key,
                        is_test=is_test, **kwargs)
        cls.session.add(new_group)
        cls.session.commit()
        return new_group

    @classmethod
    def retrieve(cls, external_id):
        # Used one() instead get() to raise error if not found...
        return cls.query.filter(cls.external_id == external_id).one()


    def delete(self):
        self.session.delete(self)
        self.session.commit()

