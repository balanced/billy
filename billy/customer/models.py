from billy.models.base import Base, JSONDict
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.schema import UniqueConstraint, ForeignKey
from sqlalchemy import and_
from pytz import UTC
from datetime import datetime
from billy.errors import AlreadyExistsError, NotFoundError, LimitReachedError
from billy.coupons.models import Coupon
from billy.invoices.models import PlanInvoice, PayoutInvoice
from decimal import Decimal
from dateutil.relativedelta import relativedelta

class Customer(Base):
    __tablename__ = 'customers'

    customer_id = Column(String, primary_key=True)
    marketplace = Column(String)
    current_payout = Column(String, ForeignKey('payouts.payout_id'))
    current_coupon = Column(String, ForeignKey('coupons.coupon_id'))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    updated_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    coupon_use = Column(JSONDict, default={})
    #Todo remove this:
    plan_use = Column(JSONDict, default={})

    __table_args__ = (UniqueConstraint('customer_id', 'marketplace', name='customerid_marketplace'),
    )


    def __init__(self, id, marketplace):
        self.customer_id = id
        self.marketplace = marketplace


    @classmethod
    def create_customer(cls, customer_id, marketplace):
        """
        Creates a customer for the marketplace.
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        :return: Customer Object if success or raises error if not
        :raise AlreadyExistsError: if customer already exists
        """
        exists = cls.query.filter(
            and_(cls.customer_id == customer_id,
                 cls.marketplace == marketplace)).first()
        if not exists:
            new_customer = Customer(customer_id, marketplace)
            cls.session.add(new_customer)
            cls.session.commit()
            return new_customer
        else:
            raise AlreadyExistsError(
                'Customer already exists. Check customer_id and marketplace')

    @classmethod
    def retrieve_customer(cls, customer_id, marketplace):
        """
        This method retrieves a single plan.
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        :return: Customer Object if success or raises error if not
        :raise NotFoundError:  if plan not found.
        """
        #TODO: Retrieve FKeys with it
        exists = cls.query.filter(
            and_(cls.customer_id == customer_id,
                 cls.marketplace == marketplace)).first()
        if not exists:
            raise NotFoundError('Customer not found. Check plan_id and marketplace')
        return exists

    @classmethod
    def list_customers(cls, marketplace):
        """
        Returns a list of customers currently in the database
        :param marketplace: The group/marketplace id/uri
        :returns: A list of Customer objects
        """
        results = cls.query.filter(
            cls.marketplace == marketplace).all()
        return results

    def apply_coupon(self, coupon_id):
        """
        Adds a coupon to the user.
        :param coupon_id:
        :return: Self
        :raise: LimitReachedError if coupon max redeemed.
        """
        coupon_obj = Coupon.retrieve_coupon(coupon_id, self.marketplace,
                                     active_only=True) #Raises NotFoundError if
        # not found
        if coupon_obj.max_redeem != -1 and coupon_obj.count_redeemed > \
                coupon_obj.max_redeem:
            raise LimitReachedError("Coupon redemtions exceeded max_redeem.")
        self.current_coupon = coupon_id
        self.updated_at = datetime.now(UTC)
        self.session.commit()
        return self

    @classmethod
    def apply_coupon_to_customer(cls, customer_id, marketplace, coupon_id):
        """
        Static version of apply_coupon
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        :return: The new Customer object
        :raise NotFoundError: If customer not found
        """
        exists = cls.query.filter(
            and_(cls.customer_id == customer_id,
                 cls.marketplace == marketplace)).first()
        if not exists:
            raise NotFoundError('Customer not found. Try different id')
        return exists.apply_coupon(coupon_id)

    def remove_coupon(self):
        """
        Removes the coupon.

        """
        if not self.current_coupon:
            return self
        self.current_coupon = None
        self.updated_at = datetime.now(UTC)
        self.session.commit()
        return self

    @classmethod
    def remove_customer_coupon(cls, customer_id, marketplace):
        """
        Removes coupon associated with customer
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        :return: The new Customer object
        :raise NotFoundError: If customer not found
        """
        exists = cls.query.filter(
            and_(cls.customer_id == customer_id,
                 cls.marketplace == marketplace)).first()
        if not exists:
            raise NotFoundError('Customer not found. Try different id')


    #Todo.. non static
    @classmethod
    def change_customer_payout(cls, customer_id, marketplace, payout_id,
                               first_now=False, cancel_scheduled=False):
        """
        Changes a customer payout schedule
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        :param payout_id: the id of the payout to asscociate with the account
        :param first_now: Whether to do the first payout immediately now or to
        schedule the first one in the future (now + interval)
        :param cancel_scheduled: Whether to cancel the next payout already
        scheduled with the old payout.
        :raise NotFoundError: if customer or payout are not found.
        :returns: The customer object.
        """
        customer_obj = cls.query.filter(
            and_(cls.customer_id == customer_id,
                 cls.marketplace == marketplace)).first()
        if not customer_obj:
            raise NotFoundError('Customer not found. Try different id')
        payout_obj = retrieve_payout(payout_id, marketplace, active_only=True)
        now = datetime.now(UTC)
        first_charge = datetime.now(UTC)
        payout_amount = payout_obj.payout_amount_cents
        if not first_now:
            first_charge += payout_obj.to_relativedelta(payout_obj.payout_interval)
        if cancel_scheduled:
            PayoutInvoice.query.filter(and_(PayoutInvoice.customer_id
                                                        == customer_id,
                                                        PayoutInvoice.marketplace
                                                        == marketplace,
                                                        PayoutInvoice.payout_date
                                                        > now))
        invoice = PayoutInvoice(customer_id, marketplace, payout_obj.payout_id,
                                first_charge, payout_amount, 0, payout_amount)
        customer_obj.current_payout = payout_obj.payout_id
        cls.session.add(invoice)
        #todo fire off task
        cls.session.commit()
        return customer_obj

    #Todo non static
    @classmethod
    def cancel_customer_payout(cls, customer_id, marketplace,
                               cancel_scheduled=False):
        """
        Cancels a customer payout
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        schedule the first one in the future (now + interval)
        :param cancel_scheduled: Whether to cancel the next payout already
        scheduled with the old payout.
        :raise NotFoundError: if customer or payout are not found.
        :returns: The customer object
        """
        now = datetime.now(UTC)
        customer = cls.retrieve_customer(customer_id, marketplace)
        if cancel_scheduled:
            PayoutInvoice.query.filter(and_(PayoutInvoice.customer_id
                                                    == customer_id,
                                                    PayoutInvoice.marketplace
                                                    == marketplace,
                                                    PayoutInvoice.payout_date
                                                    > now))

        customer.current_payout = None
        Customer.session.commit()
        return customer


    def change_plan_qty(self):
        #Todo
        pass