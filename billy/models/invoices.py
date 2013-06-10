from datetime import datetime

from pytz import UTC
from sqlalchemy import Column, Unicode, Integer, DateTime, Boolean
from sqlalchemy.schema import ForeignKey, ForeignKeyConstraint, Index

from billy.models import *
from billy.utils.models import uuid_factory
from billy.errors import NotFoundError
from billy.settings import TRANSACTION_PROVIDER_CLASS, RETRY_DELAY_PAYOUT


class PlanInvoice(Base):
    __tablename__ = 'plan_invoices'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('PLI'))
    customer_id = Column(Unicode)
    group_id = Column(Unicode)
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
    charge_at_period_end = Column(Boolean)
    active = Column(Boolean, default=True)
    cleared_by = Column(Unicode, ForeignKey('payment_transactions.guid'))

    __table_args__ = (
        #Customer foreign key
        ForeignKeyConstraint(
            [customer_id, group_id],
            [Customer.external_id, Customer.group_id]),
        #Plan foreign key
        ForeignKeyConstraint(
            [relevant_plan, group_id],
            [Plan.external_id, Plan.group_id]),
        #Coupon foreign key
        ForeignKeyConstraint(
            [relevant_coupon, group_id],
            [Coupon.external_id, Plan.group_id]),
        Index('unique_plan_invoice', relevant_plan, group_id,
              postgresql_where=active == True,
              unique=True)
    )

    @classmethod
    def retrieve_invoice(cls, customer_id, group_id, relevant_plan=None,
                         active_only=False):
        query = cls.query.filter(cls.customer_id == customer_id,
                                 cls.group_id == group_id)
        if relevant_plan:
            query.filter(cls.relevant_plan == relevant_plan)
        if active_only:
            query.filter(cls.active == True)
        exists = query.first()
        if not exists:
            raise NotFoundError('The invoice was not found. Check params.')
        return exists

    @classmethod
    def create_invoice(cls, customer_id, group_id, relevant_plan,
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
        cls.session.add(new_invoice)

    @classmethod
    def retrieve_invoice(cls, customer_id, group_id, relevant_plan=None,
                         active_only=False):
        query = cls.query.filter(cls.customer_id == customer_id,
                                 cls.group_id == group_id)
        if relevant_plan:
            query.filter(cls.relevant_plan == relevant_plan)
        if active_only:
            query.filter(cls.active == True)
        return query.first()

    @classmethod
    def list_invoices(cls, group_id, relevant_plan=None, customer_id=None,
                      active_only=False):
        query = cls.query.filter(cls.group_id == group_id)
        if customer_id:
            query.filter(cls.customer_id == customer_id)
        if active_only:
            query.filter(cls.active == True)
        if relevant_plan:
            query.filter(cls.relevant_plan == relevant_plan)
        return query.first()

    @classmethod
    def need_debt_cleared(cls):
        """
        Returns a list of customer objects that need to clear their plan debt
        """
        now = datetime.now(UTC)
        results = cls.query.filter(
            cls.remaining_balance_cents > 0,
            cls.due_dt > now,
            ).group_by(cls.customer_id).all()
        return [result.customer for result in results]

    @classmethod
    def need_rollover(cls):
        """
        Returns a list of PlanInvoice objects that need a rollover
        """
        now = datetime.now(UTC)
        invoices_rollover = cls.query.filter(cls.end_dt > now,
                                             cls.active == True,
                                             cls.remaining_balance_cents == 0,
        ).all()
        return invoices_rollover

    def rollover(self):
        """
        Rollover the invoice
        """
        self.active = False
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


class PayoutInvoice(Base):
    __tablename__ = 'payout_invoices'

    guid = Column(Unicode, primary_key=True, default=uuid_factory('POI'))
    customer_id = Column(Unicode)
    group_id = Column(Unicode)
    relevant_payout = Column(Unicode)
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    payout_date = Column(DateTime(timezone=UTC))
    balance_to_keep_cents = Column(Integer)
    amount_payed_out = Column(Integer)
    completed = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    balance_at_exec = Column(Integer)
    cleared_by = Column(Unicode, ForeignKey('payout_transactions.guid'))
    attempts_made = Column(Integer, default=0)


    __table_args__ = (
        #Customer foreign key
        ForeignKeyConstraint(
            [customer_id, group_id],
            [Customer.external_id, Customer.group_id]),
        #Payout foreign key
        ForeignKeyConstraint(
            [relevant_payout, group_id],
            [Payout.external_id, Payout.group_id]),
        Index('unique_payout_invoice', relevant_payout, group_id,
              postgresql_where=active == True, unique=True)

    )

    @classmethod
    def create_invoice(cls, customer_id, group_id, relevant_payout,
                       payout_date, balanced_to_keep_cents):
        new_invoice = cls(
            customer_id=customer_id,
            group_id=group_id,
            relevant_payout=relevant_payout,
            payout_date=payout_date,
            balanced_to_keep_cents=balanced_to_keep_cents,
        )

    @classmethod
    def retrieve_invoice(cls, customer_id, group_id, relevant_payout=None,
                         active_only=False, only_incomplete=False):
        query = cls.query.filter(cls.customer_id == customer_id,
                                 cls.group_id == group_id)
        if relevant_payout:
            query.filter(cls.relevant_payout == relevant_payout)
        if active_only:
            query.filter(cls.active == True)
        if only_incomplete:
            query.filter(cls.completed == False)
        return query.first()


    @classmethod
    def list_invoices(cls, group_id, relevant_payout=None,
                      customer_id=None, active_only=False):
        query = cls.query.filter(cls.group_id == group_id)
        if customer_id:
            query.filter(cls.customer_id == customer_id)
        if active_only:
            query.filter(cls.active == True)
        if relevant_payout:
            query.filter(cls.payout_id == relevant_payout)
        return query.first()


    @classmethod
    def needs_payout_made(cls):
        now = datetime.now(UTC)
        return cls.query.filter(cls.payout_date < now,
                         cls.completed == False
                        ).all()

    @classmethod
    def needs_rollover(cls):
        return cls.query.filter(cls.completed == True,
                                cls.active == False).all()

    def rollover(self):
        self.active = False
        self.session.flush()
        self.customer.add_payout(self.relevant_payout, first_now=False,
                                 start_dt=self.payout_date)



    def make_payout(self, force=False):
        now = datetime.now(UTC)
        current_balance = TRANSACTION_PROVIDER_CLASS.check_balance(
                                        self.customer_id, self.group_id)
        payout_date = self.payout_date
        if len(RETRY_DELAY_PAYOUT) > self.attempts_made and not force:
            self.active = False
        else:
            retry_delay = sum(RETRY_DELAY_PAYOUT[:self.attempts_made])
            when_to_payout = payout_date + retry_delay if retry_delay else \
                payout_date
            if when_to_payout < now:
                payout_amount = current_balance - self.balance_to_keep_cents
                transaction = TRANSACTION_PROVIDER_CLASS.make_payout(
                            self.customer_id, self.group_id, payout_amount)
                try:
                    transaction.execute()
                    self.cleared_by = transaction.guid
                    self.balance_at_exec = current_balance
                    self.amount_payed_out = payout_amount
                    self.completed = True
                except:
                    self.attempts_made += 1
        self.session.commit()
        return self

    @classmethod
    def make_all_payouts(cls):
        payout_invoices = cls.needs_payout_made()
        for invoice in payout_invoices:
            invoice.make_payout()
        return True

    @classmethod
    def rollover_all(cls):
        need_rollover = cls.needs_rollover()
        for payout in need_rollover:
            payout.rollover()








