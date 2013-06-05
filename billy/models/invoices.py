from billy.models.base import Base
from billy.errors import NotFoundError
from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.schema import ForeignKey, UniqueConstraint
from pytz import UTC
from datetime import datetime




class PlanInvoice(Base):
    __tablename__ = 'charge_invoices'

    invoice_id = Column(Integer, primary_key=True)
    customer_id = Column(String, ForeignKey('customers.customer_id'))
    marketplace = Column(String)
    relevant_plan = Column(String, ForeignKey('plans.plan_id'))
    relevant_coupon = Column(String, ForeignKey('coupons.coupon_id'))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    start_dt = Column(DateTime(timezone=UTC))
    end_dt = Column(DateTime(timezone=UTC))
    due_dt = Column(DateTime(timezone=UTC))
    amount_base_cents = Column(Integer)
    amount_after_coupon_cents = Column(Integer)
    amount_paid_cents = Column(Integer)
    remaining_balance_cents = Column(Integer)
    quantity = Column(Integer)
    charge_at_period_end = Column(Boolean)
    active = Column(Boolean, default=True)


    __table_args__ = (UniqueConstraint('customer_id', 'marketplace',
                                       'relevant_plan',
                      name='plan_invoice_unique'),
    )

    @classmethod
    def retrieve_invoice(cls, customer_id, marketplace, relevant_plan = None,
                         active_only = False):
        query =cls.query.filter(cls.customer_id == customer_id,
                         cls.marketplace == marketplace)
        if relevant_plan:
            query.filter(cls.relevant_plan == relevant_plan)
        if active_only:
            query.filter(cls.active == True)
        exists = query.first()
        if not exists:
            raise NotFoundError('The invoice was not found. Check params.')
        return exists

    @classmethod
    def create_invoice(cls, customer_id, marketplace, relevant_plan,
                 relevant_coupon,
                 start_dt, end_dt, due_dt,
                 amount_base_cents, amount_after_coupon_cents,
                 amount_paid_cents, remaining_balance_cents, quantity,
                 charge_at_period_end):
        new_invoice = cls(
            customer_id = customer_id,
            marketplace = marketplace,
            relevant_plan = relevant_plan,
            relevant_coupon = relevant_coupon,
            start_dt = start_dt,
            end_dt = end_dt,
            due_dt = due_dt,
            amount_base_cents = amount_base_cents,
            amount_after_coupon_cents = amount_after_coupon_cents,
            amount_paid_cents = amount_paid_cents,
            remaining_balance_cents = remaining_balance_cents,
            quantity = quantity,
            charge_at_period_end = charge_at_period_end
            )
        cls.session.add(new_invoice)

    @classmethod
    def retrieve_invoice(cls, customer_id, marketplace, relevant_plan = None,
                         active_only = False):
        query = cls.query.filter(cls.customer_id == customer_id,
                                 cls.marketplace == marketplace)
        if relevant_plan:
            query.filter(cls.relevant_plan == relevant_plan)
        if active_only:
            query.filter(cls.active == True)
        return query.first()

    @classmethod
    def list_invoices(cls, market_place, relevant_plan=None, customer_id = None,
                      active_only=False):
        query = cls.query.filter(cls.marketplace == market_place)
        if customer_id:
            query.filter(cls.customer_id == customer_id)
        if active_only:
            query.filter(cls.active == True)
        if relevant_plan:
            query.filter(cls.relevant_plan == relevant_plan)
        return query.first()


class PayoutInvoice(Base):
    __tablename__ = 'payout_invoices'

    invoice_id = Column(Integer, primary_key=True)
    customer_id = Column(String, ForeignKey('customers.customer_id'))
    marketplace = Column(String)
    relevant_payout = Column(String, ForeignKey('plans.plan_id'))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    payout_date = Column(DateTime(timezone=UTC))
    balance_to_keep_cents = Column(Integer)
    amount_payed_out = Column(Integer)
    completed = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    #Todo: make sure yo update this field...
    balance_at_exec = Column(Integer)

    __table_args__ = (UniqueConstraint('customer_id', 'marketplace',
                                       'relevant_payout',
                                       name='payout_invoice_unique'))

    @classmethod
    def create_invoice(cls, customer_id, marketpalce, relevant_payout,
                       payout_date, balanced_to_keep_cents):
        new_invoice = cls(
            customer_id = customer_id,
            marketpalce = marketpalce,
            relevant_payout = relevant_payout,
            payout_date = payout_date,
            balanced_to_keep_cents = balanced_to_keep_cents,
        )

    @classmethod
    def retrieve_invoice(cls, customer_id, marketplace, relevant_payout = None,
                        active_only = False, only_incomplete=False):
        query = cls.query.filter(cls.customer_id == customer_id,
                                 cls.marketplace == marketplace)
        if relevant_payout:
            query.filter(cls.relevant_payout == relevant_payout)
        if active_only:
            query.filter(cls.active == True)
        if only_incomplete:
            query.filter(cls.completed == False)
        return query.first()


    @classmethod
    def list_invoices(cls, market_place, relevant_payout=None,
                      customer_id = None, active_only=False):
        query = cls.query.filter(cls.marketplace == market_place)
        if customer_id:
            query.filter(cls.customer_id == customer_id)
        if active_only:
            query.filter(cls.active == True)
        if relevant_payout:
            query.filter(cls.payout_id == relevant_payout)
        return query.first()
