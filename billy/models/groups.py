from __future__ import unicode_literals

from sqlalchemy import Unicode, Column, Enum, Boolean
from sqlalchemy.orm import relationship

from models import Base, Customer, Coupon
from processor import processor_map
from utils.generic import api_key_factory, uuid_factory


class Company(Base):
    __tablename__ = 'company'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('GR'))
    api_key = Column(Unicode, unique=True, default=api_key_factory())
    processor_type = Column(Enum('BALANCED', 'DUMMY', name='provider_enum'),
                            nullable=False)
    processor_api_key = Column(Unicode, nullable=False)
    processor_company_id = Column(Unicode, nullable=False, unique=True)
    is_test = Column(Boolean, default=True)

    coupons = relationship('Coupon', backref='company', lazy='dynamic',
                           cascade='delete',)
    customers = relationship('Customer', backref='company', cascade='delete')
    plans = relationship('ChargePlan', backref='company', lazy='dynamic',
                         cascade='delete')
    payouts = relationship('Payout', backref='company', lazy='dynamic',
                           cascade='delete')

    @classmethod
    def create(cls, external_id, processor_type, processor_api_key,
               is_test=True, **kwargs):
        # Some sort of check api_key thingy.
        processor_class = processor_map[processor_type]
        process_company_id = processor_class.get_comapany_id(processor_api_key)
        new_company = cls(external_id=external_id,
                          processor_type=processor_type,
                          processor_api_key=processor_api_key,
                          process_company_id=process_company_id,
                          is_test=is_test, **kwargs)
        cls.session.add(new_company)
        cls.session.commit()
        return new_company


    def create_customer(self, external_id, provider_id):
        """
        Creates a new customer under the company.
        """
        new_customer = Customer(
            external_id=external_id,
            provider_id=provider_id,
            group_id=self.guid
        )
        self.session.add(new_customer)
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise
        return new_customer


    def create_coupon(self, external_id, name, price_off_cents,
                      percent_off_int, max_redeem, repeating, expire_at=None):
        """
        Creates a new coupon for the company
        """
        new_coupon = Coupon(
            external_id=external_id,
            group_id=self.guid,
            name=name,
            price_off_cents=price_off_cents,
            percent_off_int=percent_off_int,
            max_redeem=max_redeem,
            repeating=repeating,
            expire_at=expire_at)
        self.session.add(new_coupon)
        try:
            self.session.commit()
        except:
            self.session.rollback()
            raise
        return new_coupon


    def delete(self, force=False):
        if not self.is_test and not force:
            raise Exception('Can only delete test marketplaces without '
                            'force set to true.')
        self.session.delete(self)
        self.session.commit()

    @property
    def processor_class(self):
        return processor_map[self.processor_type]


