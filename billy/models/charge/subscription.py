from datetime import datetime
from sqlalchemy import Column, Unicode, ForeignKey, Boolean, Index, func
from models import Base
from utils.models import uuid_factory


class ChargeSubscription(Base):
    __tablename__ = 'charge_subscription'

    id = Column(Unicode, primary_key=True, default=uuid_factory('CS'))
    customer_id = Column(Unicode, ForeignKey('customers.id'), nullable=False)
    coupon_id = Column(Unicode, ForeignKey('coupons.id'))
    plan_id = Column(Unicode, ForeignKey('charge_plans.id'), nullable=False)
    # is_enrolled and should_renew have paired states such as:
    # 1) is_enrolled = True and should_renew = False when the subscription will
    # end at the end of the current period
    # 2) is_enrolled = True nd should_renew = True when the customer is on the
    # plan and will continue to be on it
    # 3) is_enrolled = False and should_renew = False when the customer is
    # neither enrolled or will it renew
    is_enrolled = Column(Boolean, default=True)
    should_renew = Column(Boolean, default=True)

    __table_args__ = (
        Index('unique_charge_sub', plan_id, customer_id,
              postgresql_where=should_renew == True,
              unique=True),
    )

    @classmethod
    def create(cls, customer, plan, coupon=None):
        subscription = cls.query.filter(
            cls.customer_id == customer.id,
            cls.plan_id == plan.id
        ).first()
        subscription = subscription or cls(
            customer_id=customer.id, plan_id=plan.id, coupon=coupon)
        subscription.should_renew = True
        subscription.is_enrolled = True
        cls.session.add(subscription)
        return subscription

    @property
    def current_invoice(self):
        """
        Returns the current invoice of the customer. There can only be one
        invoice outstanding per customer ChargePlan
        """
        from models import ChargePlanInvoice

        return self.invoices.filter(
            ChargePlanInvoice.end_dt > datetime.utcnow()).first()

    def cancel(self):
        from models import ChargePlanInvoice
        self.is_enrolled = False
        self.should_renew = False
        ChargePlanInvoice.prorate_last(self.customer, self.plan)
        return self


    def generate_next_invoice(self):
        """
        Rollover the invoice if the next invoice is not already there.
        """
        from models import ChargePlanInvoice

        customer = self.customer
        plan = self.plan
        if self.current_invoice:
            return self.current_invoice
        last_invoice = self.query.join(ChargePlanInvoice).order_by(
            ChargePlanInvoice.end_dt.desc()).first()
        sub = plan.subscribe(
            customer=customer,
            quantity=last_invoice.quantity,
            charge_at_period_end=last_invoice.charge_at_period_end,
            start_dt=last_invoice.end_dt)
        return sub.current_invoice


    @classmethod
    def generate_all_invoices(cls):
        """
        Generate the next invoice for all invoices that need to be generated
        """
        from models import ChargePlanInvoice

        now = datetime.utcnow()
        needs_make_invoicing = ChargeSubscription.query.join(
            ChargePlanInvoice).filter(
            cls.is_enrolled == True,
            cls.should_renew == True, ).having(
            func.max(ChargePlanInvoice.end_dt) <= now).all()
        for subscription in needs_make_invoicing:
            subscription.generate_next_invoice()
        return len(needs_make_invoicing)
