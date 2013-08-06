from __future__ import unicode_literals

from sqlalchemy import Unicode, Column, Enum, Boolean
from sqlalchemy.orm import relationship

from models import Base
from processor import processor_map
from utils.generic import api_key_factory, uuid_factory


class Company(Base):
    __tablename__ = 'company'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('GR'))
    api_key = Column(Unicode, unique=True, default=api_key_factory())
    processor_type = Column(Enum('BALANCED', 'DUMMY', name='provider_enum'),
                            nullable=False)
    processor_api_key = Column(Unicode, nullable=False, unique=True)
    processor_company_id = Column(Unicode, nullable=False, unique=True)
    is_test = Column(Boolean, default=True)

    coupons = relationship('Coupon', backref='company', lazy='dynamic',
                           cascade='delete', )
    customers = relationship('Customer', backref='company', cascade='delete')
    charge_plans = relationship(
        'ChargePlan', backref='company', lazy='dynamic',
        cascade='delete, delete-orphan')
    payout_plans = relationship(
        'PayoutPlan', backref='company', lazy='dynamic',
        cascade='delete, delete-orphan')

    @classmethod
    def create(cls, processor_type, processor_api_key,
               is_test=True, **kwargs):
        # Some sort of check api_key thingy.
        processor_class = processor_map[processor_type.upper()](processor_api_key)
        processor_company_id = processor_class.get_company_id()
        new_company = cls(
                          processor_type=processor_type,
                          processor_api_key=processor_api_key,
                          processor_company_id=processor_company_id,
                          is_test=is_test, **kwargs)
        cls.session.add(new_company)
        return new_company

    def update(self, new_api_key):
        """
        Helper method to update a companies API key
        """
        processor_company_id = self.processor.get_company(new_api_key)
        if not processor_company_id == self.processor_company_id:
            raise ValueError(
                'New API key does not match company ID with processor')
        else:
            self.processor_api_key = new_api_key
        return self

    def create_customer(self, your_id, provider_id):
        """
        Creates a new customer under the company.
        """
        from models import Customer
        new_customer = Customer(
            your_id=your_id,
            processor_id=provider_id,
            company_id=self.guid
        )
        self.session.add(new_customer)
        return new_customer

    def add_coupon(self, your_id, name, price_off_cents,
                   percent_off_int, max_redeem, repeating, expire_at=None):
        """
        Creates a new coupon for the company
        """
        from models import Coupon
        new_coupon = Coupon(
            your_id=your_id,
            company_id=self.guid,
            name=name,
            price_off_cents=price_off_cents,
            percent_off_int=percent_off_int,
            max_redeem=max_redeem,
            repeating=repeating,
            expire_at=expire_at)
        self.session.add(new_coupon)
        return new_coupon

    def create_charge_plan(self, your_id, name, price_cents,
                        plan_interval, trial_interval):
        """
        Creates a charge plan under the company
        """
        from models import ChargePlan
        new_plan = ChargePlan(
            your_id=your_id,
            company_id=self.guid,
            name=name,
            price_cents=price_cents,
            plan_interval=plan_interval,
            trial_interval=trial_interval
        )
        self.session.add(new_plan)
        return new_plan

    def create_payout_plan(self, your_id, name, balance_to_keep_cents,
                        payout_interval):
        """
        Creates a payout plan under the company
        """
        from models import PayoutPlan
        new_payout = PayoutPlan(
            your_id=your_id,
            company_id=self.guid,
            name=name,
            balance_to_keep_cents=balance_to_keep_cents,
            payout_interval=payout_interval)
        self.session.add(new_payout)
        return new_payout

    def delete(self, force=False):
        if not self.is_test and not force:
            raise Exception('Can only delete test marketplaces without '
                            'force set to true.')
        self.session.delete(self)

    @property
    def processor(self):
        """
        Returns the instantiated processor class
        """
        return processor_map[self.processor_type](self.api_key)
