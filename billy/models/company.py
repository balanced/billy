from __future__ import unicode_literals

from sqlalchemy import Unicode, Column, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref

from models import Base, ProcessorType, PayoutPlan, ChargePlan, Coupon, Customer
from processor import processor_map
from utils.models import api_key_factory, uuid_factory


class Company(Base):
    __tablename__ = 'companies'

    id = Column(Unicode, primary_key=True, default=uuid_factory('CP'))

    #: The processor to use for this company
    processor_type = Column(ProcessorType, nullable=False)

    #: The credentials/api key that works with the company
    processor_credential = Column(Unicode, nullable=False, unique=True)

    #: The id of this company with the processor
    processor_company_id = Column(Unicode, nullable=False, unique=True)

    #: Deletion is supported only on test companies with this flag set to true
    is_test = Column(Boolean, default=True)

    # Todo: make this a separate table
    #: Api key for billy-api
    api_key = Column(Unicode, nullable=False, default=api_key_factory())

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
    def create(cls, processor_type, processor_credential,
               is_test=True, **kwargs):
        """
        Creates a company
        """

        # Todo Some sort of check api_key thingy.
        processor_class = processor_map[
            processor_type.upper()](processor_credential)
        processor_company_id = processor_class.get_company_id()
        company = cls(
            processor_type=processor_type.upper(),
            processor_credential=processor_credential,
            processor_company_id=processor_company_id,
            is_test=is_test, **kwargs)
        cls.session.add(company)
        return company

    def change_processor_credential(self, processor_credential):
        """
        Updates the company's processor credentials
        :param processor_credential: The new credentials
        :return: the updated Company object
        :raise: ValueError if the processor_company_id doesn't match the one
        associated with the new api key
        """
        processor_company_id = self.processor.get_company(
            processor_credential)
        if not processor_company_id == self.processor_company_id:
            raise ValueError(
                'New API key does not match company ID with models.processor')
        else:
            self.processor_credential = processor_credential
        return self

    def create_customer(self, your_id, processor_id):
        customer = Customer(
            your_id=your_id,
            processor_id=processor_id,
            company=self
        )
        self.session.add(customer)
        return customer

    def create_coupon(self, your_id, name, price_off_cents,
                      percent_off_int, max_redeem, repeating, expire_at=None):
        """
        Create a coupon under the company
        :param your_id: The ID you use to identify the coupon in your database
        :param name: A name for the coupon for display purposes
        :param price_off_cents: The price off in cents
        :param percent_off_int: The percent off (0-100)
        :param max_redeem: The maximum number of different subscriptions that
        can redeem the coupon -1 for unlimited or int
        :param repeating: How many invoices can this coupon be used for each
        customer? -1 for unlimited or int
        :param expire_at: When should the coupon expire?
        :return: A Coupon object
        """
        coupon= Coupon(
            your_id=your_id,
            company=self,
            name=name,
            price_off_cents=price_off_cents,
            percent_off_int=percent_off_int,
            max_redeem=max_redeem,
            repeating=repeating,
            expire_at=expire_at)
        self.session.add(coupon)

        return coupon


    def create_charge_plan(self, your_id, name, price_cents,
                           plan_interval, trial_interval):
        """
        Creates a charge plan under the company
        :param your_id: A unique ID you will use to identify this plan i.e
        STARTER_PLAN
        :param name: A display name for the plan
        :param price_cents: The price in cents to charge th customer on each
        interval
        :param plan_interval: How often does the plan recur? (weekly, monthly)
        This is a RelativeDelta object.
        :param trial_interval: The initial interval for the trial before
        charging the customer. RelativeDelta object.
        :return: A ChargePlan object
        """
        plan = ChargePlan(
            your_id=your_id,
            company=self,
            name=name,
            price_cents=price_cents,
            plan_interval=plan_interval,
            trial_interval=trial_interval
        )
        self.session.add(plan)
        return plan

    def create_payout_plan(self, your_id, name, balance_to_keep_cents,
                           payout_interval):
        """
        Creates a payout plan under the company
        :param your_id: What you identify this payout plan as. e.g MY_PAYOUT
        :param name: A display name for the payout
        :param balance_to_keep_cents: Balance to keep after the payout, this is
        how payout amounts are determined balance - balance_to_keep = payout_amount
        :param payout_interval: How often should this payout be conducted?
        A relative delta object
        :return: A PayoutPlan object
        """
        payout = PayoutPlan(
            your_id=your_id,
            company=self,
            name=name,
            balance_to_keep_cents=balance_to_keep_cents,
            payout_interval=payout_interval)
        self.session.add(payout)
        return payout

    def delete(self, force=False):
        if not self.is_test and not force:
            raise Exception('Can only delete test marketplaces without '
                            'force set to true.')
        self.session.delete(self)
        self.session.commit()

    @property
    def processor(self):
        """
        Get an instantiated processor for the company i.e DummyProcessor
        :return: An instantiated ProcessorClass
        """
        return processor_map[self.processor_type](self.processor_credential)
