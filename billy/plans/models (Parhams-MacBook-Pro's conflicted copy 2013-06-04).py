from billy.models.base import Base, JSONDict
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.schema import UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from pytz import UTC
from datetime import datetime
from dateutil.relativedelta import relativedelta
from billy.errors import BadIntervalError
from billy.customer.models import Customer
from billy.invoices.models import PlanInvoice
from billy.errors import NotFoundError, AlreadyExistsError
from sqlalchemy import and_
from decimal import Decimal



class Plan(Base):
    __tablename__ = 'plans'

    plan_id = Column(String, primary_key=True)
    marketplace = Column(String)
    name = Column(String)
    price_cents = Column(Integer)

    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=UTC))
    updated_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    trial_interval = Column(JSONDict)
    plan_interval = Column(JSONDict)
    customers = relationship(Customer.__name__, backref='plans')

    #Todo end of period
    __table_args__ = (
    UniqueConstraint('plan_id', 'marketplace', name='planid_marketplace'),
    )


    def __init__(self, id, marketplace, name, price_cents, plan_interval,
                 trial_interval):
        self.plan_id = id
        self.name = name
        self.price_cents = price_cents
        if not isinstance(plan_interval, relativedelta):
            raise BadIntervalError(
                "plan_interval must be a relativedelta type.")
        else:
            self.plan_interval = self.from_relativedelta(plan_interval)
        if not isinstance(trial_interval, relativedelta):
            raise BadIntervalError(
                "trial_interval must be a relativedelta type.")
        else:
            self.trial_interval = self.from_relativedelta(trial_interval)
        self.marketplace = marketplace

    def from_relativedelta(self, inter):
        return {
            'years': inter.years,
            'months': inter.months,
            'days': inter.days,
            'hours': inter.hours,
            'minutes': inter.minutes
        }

    def to_relativedelta(self, param):
        return relativedelta(years=param['years'], months=param['months'],
                             days=param['days'], hours=param['hours'],
                             minutes=param['minutes'])


    @classmethod
    def create_plan(cls, plan_id, marketplace, name, price_cents,
                    plan_interval, trial_interval):
        """
        Creates a plan that users can be assigned to.
        :param plan_id: A unique id/uri for the plan
        :param marketplace: a group/marketplace id/uri the user should be placed in (matches balanced payments marketplaces)
        :param name: A display name for the plan
        :param price_cents: Price in cents of the plan per interval. $1.00 = 100
        :param plan_interval: A Interval class that defines how frequently the charge the plan
        :param trial_interval: A Interval class that defines how long the initial trial is
        :return: Plan Object if success or raises error if not
        :raise AlreadyExistsError: if plan already exists
        :raise TypeError: if intervals are not relativedelta (Interval class)
        """
        exists = cls.query.filter(and_(cls.plan_id == plan_id,
                               cls.marketplace == marketplace)).first()
        if not exists:
            new_plan = Plan(plan_id, marketplace, name, price_cents, plan_interval, trial_interval)
            cls.session.add(new_plan)
            cls.session.commit()
            return new_plan
        else:
            raise AlreadyExistsError('Plan already exists. Check plan_id and marketplace')

    @classmethod
    def retrieve_plan(cls, plan_id, marketplace, active_only=False):
        """
        This method retrieves a single plan.
        :param plan_id: the unique plan_id
        :param marketplace: the plans marketplace/group
        :param active_only: if true only returns active plans
        :raise NotFoundError:  if plan not found.
        """
        if active_only:
            and_filter = and_(cls.plan_id == plan_id,
                              cls.marketplace == marketplace,
                              cls.active == True)
        else:
            and_filter = and_(cls.plan_id == plan_id,
                              cls.marketplace == marketplace)
        exists = cls.query.filter(and_filter).first()
        if not exists:
            raise NotFoundError('Active Plan not found. Check plan_id and marketplace')
        return exists
    #Todo model methods
    @classmethod
    def update_plan(cls, plan_id, marketplace, new_name):
        """
        Updates ONLY the plan name. By design the only updateable field is the name.
        To change other params create a new plan.
        :param plan_id: The plan id/uri
        :param marketplace: The group/marketplace id/uri
        :param new_name: The new display name for the plan
        :raise NotFoundError:  if plan not found.
        :returns: New Plan object
        """
        exists = cls.query.filter(and_(cls.plan_id == plan_id,
                               cls.marketplace == marketplace)).first()
        if not exists:
            raise NotFoundError('Plan not found. Try different id')
        exists.name = new_name
        exists.updated_at = datetime.now(UTC)
        cls.session.commit()
        return exists

    @classmethod
    def list_plans(cls, marketplace):
        #Todo active only
        """
        Returns a list of plans currently in the database
        :param marketplace: The group/marketplace id/uri
        :returns: A list of Plan objects
        """
        results = cls.query.filter(cls.marketplace == marketplace).all()
        return results


    @classmethod
    def delete_plan(cls, plan_id, marketplace):
        """
        This method deletes a plan. Plans are not deleted from the database, but are instead marked as inactive so no new
        users can be added. Everyone currently on the plan is maintained on the plan.
        :param plan_id: the unique plan_id
        :param marketplace: the plans marketplace/group
        :returns: the deleted Plan object
        :raise NotFoundError:  if plan not found.
        """
        exists = cls.query.filter(and_(cls.plan_id == plan_id,
                               cls.marketplace == marketplace)).first()
        if not exists:
            raise NotFoundError('Plan not found. Use different id')
        exists.active = False
        exists.updated_at = datetime.now(UTC)
        exists.deleted_at = datetime.now(UTC)
        cls.session.commit()
        return exists


class PlanSubscription(Base):

    __tablename__ = 'plan_sub'

    sub_id = Column(String, primary_key=True)
    marketplace = Column(String)
    customer_id = Column(String, ForeignKey('customers.customer_id'))
    plan_id = Column(String,  ForeignKey('plans.plan_id'))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    cycle_start = Column(DateTime(timezone=UTC))
    charge_at_period_end = Column(Boolean)
    active = Column(Boolean, default=True)
    inactivated_on = Column(DateTime(timezone=UTC))
    quantity = Column(Integer)


    @classmethod
    def retrieve_subscription(cls, customer_id, marketplace, plan_id,
                              active_only = True):
        if active_only:
            and_param = and_(cls.customer_id == customer_id,
                             cls.marketplace == marketplace,
                             cls.plan_id == plan_id, cls.active == True)
        else:
            and_param = and_(cls.customer_id == customer_id,
                             cls.marketplace == marketplace,
                             cls.plan_id == plan_id)
        exists = cls.query.filter(and_param).first()
        if not exists:
            raise NotFoundError("The plan you requested was not found.")
        return exists

    @classmethod
    def change_subscription(cls, customer_id, marketplace, plan_id,
                             quantity, charge_at_period_end=False):
        """
        Changes a customer's plan
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        :param plan_id: The plan id to assocaite customer with
        :raise:
        """
        customer_obj = Customer.retrieve_customer(customer_id, marketplace)
        plan_obj = Plan.retrieve_plan(plan_id, marketplace, active_only=True)
        current_coupon = customer_obj.coupon
        start_date = datetime.now(UTC)
        due_on = datetime.now(UTC)
        coupon_use_count = customer_obj.coupon_use.get(current_coupon
                                                        .coupon_id, 0)
        use_coupon = True if current_coupon.repeating == -1 or coupon_use_count \
                             <= current_coupon.repeating else False
        can_trial = True if customer_obj.plan_use.get(plan_obj.plan_id,
                                              0) == 0 else False
        end_date = start_date + plan_obj.to_relativedelta(plan_obj.plan_interval)
        trial_interval = plan_obj.to_relativedelta(plan_obj.trial_interval)
        if can_trial:
            end_date += trial_interval
            due_on += trial_interval
        if quantity < 1:
            raise ValueError("Quanity must be greater than 1")
        amount_base = plan_obj.price_cents * Decimal(quantity)
        amount_after_coupon = amount_base
        amount_paid = 0
        balance = amount_after_coupon - amount_paid
        coupon_id = current_coupon.coupon_id if current_coupon else None
        if use_coupon and current_coupon:
            dollars_off = current_coupon.price_off_cents
            percent_off = current_coupon.percent_off_int
            amount_after_coupon -= dollars_off #BOTH CENTS, safe
            amount_after_coupon -= int(
                amount_after_coupon * Decimal(percent_off) / Decimal(100))

        PlanInvoice.create_invoice(customer_id, marketplace, plan_id, coupon_id,
                                    start_date, end_date, due_on, amount_base,
                                    amount_after_coupon, amount_paid, balance)
        new_sub = PlanSubscription()
        new_sub.plan_id = plan_id
        new_sub.marketplace = marketplace
        new_sub.customer_id = customer_id
        new_sub.cycle_start = start_date
        new_sub.charge_at_period_end = charge_at_period_end
        cls.session.add(new_sub)
        customer_obj.coupon_use[coupon_id] += 1
        cls.prorate_last_invoice(customer_obj.customer_id, marketplace, plan_id)
        #Todo close old customer object
        try:
            sub_obj = cls.retrieve_subscription(customer_id, marketplace,
                                                plan_id, active_only=True)
            sub_obj.active = False
            sub_obj.inactivated_on = datetime.now(UTC)
        except NotFoundError:
            pass
        cls.session.commit()
        #Todo send off task for due_on and sum the invoices that the balance

        return customer_obj



    def cancel_subscription(self):
        """
        Cancels the customers subscription. You can either do it immediately
        or at the end of the period.
         in (matches balanced payments marketplaces)
        :param at_period_end: Whether to cancel now or wait till the user
        :returns: New customer object.
        """
        self.prorate_last_invoice(self.customer_id, self.marketplace)
        self.current_plan = None
        self.plan = None
        self.session.commit()
        return self

    @classmethod
    def cancel_customer_plan(cls, customer_id, marketplace,
                             cancel_at_period_end=True):
        """
        Cancels a customers subscription. You can either do it immediately or
        at the end of the period.
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        :param cancel_at_period_end: Whether to cancel now or wait till the user
        :returns: New customer object.
        """
        sub_obj = cls.retrieve_customer(customer_id, marketplace)
        if cancel_at_period_end:
            #Todo schedule task that removes the plan at the end of the period,
            # make sure happens before renewal
            pass
        else:
            return cls.cancel_plan(cancel_at_period_end)

    @classmethod
    def prorate_last_invoice(cls, customer_id, marketplace, plan_id):
        """
        Prorates the last invoice when changing a users plan. Only use when
        changing a users plan.
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        """
        right_now = datetime.now(UTC)
        last_invoice = PlanInvoice.query.filter(
            and_(PlanInvoice.customer_id == customer_id,
                 PlanInvoice.marketplace == marketplace,
                 PlanInvoice.end_dt > right_now)).first()
        if last_invoice:
            time_total = Decimal(
                (last_invoice.end_dt - last_invoice.due_dt).total_seconds())
            time_used = Decimal((last_invoice.start_dt - right_now).total_seconds())
            percent_used = time_used / time_total
            new_base_amount = last_invoice.amount_base_cents * percent_used
            new_coupon_amount = last_invoice.amount_after_coupon_cents * \
                                percent_used
            new_balance = last_invoice.amount_after_coupon_cents - last_invoice \
                .amount_paid_cents
            last_invoice.amount_base_cents = new_base_amount
            last_invoice.amount_after_coupon_cents = new_coupon_amount
            last_invoice.remaining_balance_cents = new_balance
            last_invoice.end_dt = right_now - relativedelta(
                seconds=30) #Extra safety for find query
        cls.session.flush()


