from __future__ import unicode_literals
from datetime import datetime

from pytz import UTC
from sqlalchemy import Column, Unicode, ForeignKey, DateTime, Boolean, \
    Integer, ForeignKeyConstraint, Index, distinct
from sqlalchemy.orm import relationship

from billy.models import Base, Group, Customer, Plan, Coupon
from billy.utils.billy_action import ActionCatalog
from billy.utils.models import uuid_factory


class PlanInvoice(Base):
    __tablename__ = 'plan_invoices'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PLI'))
    customer_id = Column(Unicode)
    group_id = Column(Unicode, ForeignKey(Group.external_id))
    relevant_plan = Column(Unicode)
    relevant_coupon = Column(Unicode)
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    start_dt = Column(DateTime(timezone=UTC))
    end_dt = Column(DateTime(timezone=UTC))
    original_end_dt = Column(DateTime(timezone=UTC))
    due_dt = Column(DateTime(timezone=UTC))
    includes_trial = Column(Boolean)
    amount_base_cents = Column(Integer)
    amount_after_coupon_cents = Column(Integer)
    amount_paid_cents = Column(Integer)
    remaining_balance_cents = Column(Integer)
    quantity = Column(Integer)
    prorated = Column(Boolean)
    charge_at_period_end = Column(Boolean)
    active = Column(Boolean, default=True)
    cleared_by = Column(Unicode, ForeignKey('plan_transactions.guid'))

    plan = relationship('Plan', backref='invoices',
                        foreign_keys=[relevant_plan, group_id])

    __table_args__ = (
        # Customer foreign key
        ForeignKeyConstraint(
            ['customer_id', 'group_id'],
            ['customers.external_id', 'customers.group_id']),
        # Plan foreign key
        ForeignKeyConstraint(
            [relevant_plan, group_id],
            [Plan.external_id, Plan.group_id]),
        # Coupon foreign key
        ForeignKeyConstraint(
            [relevant_coupon, group_id],
            [Coupon.external_id, Coupon.group_id]),
        Index('unique_plan_invoice', relevant_plan, group_id, customer_id,
              postgresql_where=active == True,
              unique=True)
    )

    @classmethod
    def create(cls, customer_id, group_id, relevant_plan,
                       relevant_coupon,
                       start_dt, end_dt, due_dt,
                       amount_base_cents, amount_after_coupon_cents,
                       amount_paid_cents, remaining_balance_cents, quantity,
                       charge_at_period_end, includes_trial=False):
        new_invoice = cls(
            customer_id=customer_id,
            group_id=group_id,
            relevant_plan=relevant_plan,
            relevant_coupon=relevant_coupon,
            start_dt=start_dt,
            end_dt=end_dt,
            due_dt=due_dt,
            original_end_dt=end_dt,
            amount_base_cents=amount_base_cents,
            amount_after_coupon_cents=amount_after_coupon_cents,
            amount_paid_cents=amount_paid_cents,
            remaining_balance_cents=remaining_balance_cents,
            quantity=quantity,
            charge_at_period_end=charge_at_period_end,
            includes_trial=includes_trial,
        )
        new_invoice.event = ActionCatalog.PI_CREATE
        cls.session.add(new_invoice)
        cls.session.commit()
        return new_invoice

    @classmethod
    def retrieve(cls, customer_id, group_id, relevant_plan=None,
                         active_only=False):
        query = cls.query.filter(cls.customer_id == customer_id,
                                 cls.group_id == group_id)
        if relevant_plan:
            query = query.filter(cls.relevant_plan == relevant_plan)
        if active_only:
            query = query.filter(cls.active == True)
        if relevant_plan and active_only:
            return query.one()
        else:
            return query.first()

    @classmethod
    def list(cls, group_id, relevant_plan=None, customer_id=None,
                      active_only=False):
        query = cls.query.filter(cls.group_id == group_id)
        if customer_id:
            query = query.filter(cls.customer_id == customer_id)
        if active_only:
            query = query.filter(cls.active == True)
        if relevant_plan:
            query = query.filter(cls.relevant_plan == relevant_plan)
        return query.all()

    @classmethod
    def need_debt_cleared(cls):
        """
        Returns a list of customer objects that need to clear their plan debt
        """
        now = datetime.now(UTC)
        results = cls.session.query(distinct(cls.customer_id)).filter(
            cls.remaining_balance_cents > 0,
            cls.due_dt <= now).all()
        for each in results:
            print each
        return [result.customer for result in results]

    @classmethod
    def need_rollover(cls):
        """
        Returns a list of PlanInvoice objects that need a rollover
        """
        now = datetime.now(UTC)
        invoices_rollover = cls.query.filter(cls.end_dt <= now,
                                             cls.active == True,
                                             cls.remaining_balance_cents == 0,
                                            ).all()
        return invoices_rollover

    def rollover(self):
        """
        Rollover the invoice
        """
        self.active = False
        self.event = ActionCatalog.PI_ROLLOVER
        self.session.flush()
        Customer.add_plan_customer(self.customer_id, self.group_id,
                                   self.relevant_plan,
                                   quantity=self.quantity,
                                   charge_at_period_end=self
                                   .charge_at_period_end,
                                   start_dt=self.end_dt)
        self.session.commit()

    @classmethod
    def rollover_all(cls):
        to_rollover = cls.need_rollover()
        for plan_invoice in to_rollover:
            plan_invoice.rollover()
        return True

    @classmethod
    def clear_all_plan_debt(cls):
        for customer in cls.need_plan_debt_cleared():
            customer.clear_plan_debt()
