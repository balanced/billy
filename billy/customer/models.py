from billy.models.base import Base, JSONDict
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.schema import UniqueConstraint, ForeignKey
from pytz import UTC
from datetime import datetime


class Customer(Base):
    __tablename__ = 'customers'

    customer_id = Column(String, primary_key=True)
    marketplace = Column(String)
    current_plan = Column(String, ForeignKey('plans.plan_id',
                                             ondelete='cascade'))
    current_payout = Column(String, ForeignKey('payouts.payout_id'))
    current_coupon = Column(String, ForeignKey('coupons.coupon_id'))
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    updated_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    periods_on_plan = Column(Integer)
    coupon_use = Column(JSONDict, default={})
    plan_use = Column(JSONDict, default={})

    __table_args__ = (UniqueConstraint('customer_id', 'marketplace', name='customerid_marketplace'),
    )


    def __init__(self, id, marketplace):
        self.customer_id = id
        self.marketplace = marketplace


    @classmethod
    def create_customer(customer_id, marketplace):
        """
        Creates a customer for the marketplace.
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        :return: Customer Object if success or raises error if not
        :raise AlreadyExistsError: if customer already exists
        """
        exists = Customer.query.filter(
            and_(Customer.customer_id == customer_id,
                 Customer.marketplace == marketplace)).first()
        if not exists:
            new_customer = Customer(customer_id, marketplace)
            query_tool.add(new_customer)
            query_tool.commit()
            return new_customer
        else:
            raise AlreadyExistsError(
                'Customer already exists. Check customer_id and marketplace')
    def retrieve_customer(customer_id, marketplace):
        """
        This method retrieves a single plan.
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        :return: Customer Object if success or raises error if not
        :raise NotFoundError:  if plan not found.
        """
        #TODO: Retrieve FKeys with it
        exists = query_tool.query(Customer).filter(
            and_(Customer.customer_id == customer_id,
                 Customer.marketplace == marketplace)).first()
        if not exists:
            raise NotFoundError('Customer not found. Check plan_id and marketplace')
        return exists


    def list_customers(marketplace):
        """
        Returns a list of customers currently in the database
        :param marketplace: The group/marketplace id/uri
        :returns: A list of Customer objects
        """
        results = query_tool.query(Customer).filter(
            Customer.marketplace == marketplace).all()
        return results


    def apply_coupon_to_customer(customer_id, marketplace, coupon_id):
        """
        Removes coupon associated with customer
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        :return: The new Customer object
        :raise NotFoundError: If customer not found
        """
        #Todo Increase use count disable if greater
        exists = query_tool.query(Customer).filter(
            and_(Customer.customer_id == customer_id,
                 Customer.marketplace == marketplace)).first()
        if not exists:
            raise NotFoundError('Customer not found. Try different id')
        coupon_obj = retrieve_coupon(coupon_id, marketplace,
                                     active_only=True) #Raises NotFoundError if
        # not found
        if coupon_obj.max_redeem != -1 and coupon_obj.count_redeemed > \
                coupon_obj.max_redeem:
            raise LimitReachedError("Coupon redemtions exceeded max_redeem.")
        exists.current_coupon = coupon_id
        exists.updated_at = datetime.now(UTC)
        query_tool.commit()
        return exists


    def remove_customer_coupon(customer_id, marketplace):
        """
        Removes coupon associated with customer
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        :return: The new Customer object
        :raise NotFoundError: If customer not found
        """
        #Todo reduce redeem count disable if less
        exists = query_tool.query(Customer).filter(
            and_(Customer.customer_id == customer_id,
                 Customer.marketplace == marketplace)).first()
        if not exists:
            raise NotFoundError('Customer not found. Try different id')
        if not exists.current_coupon:
            return exists
        exists.current_coupon = None
        exists.updated_at = datetime.now(UTC)
        query_tool.commit()
        return exists


    def change_customer_plan(customer_id, marketplace, plan_id):
        """
        #Todo
        :param customer_id:
        :param marketplace:
        :param plan_id:
        :raise:
        """
        customer_obj = query_tool.query(Customer).filter(
            and_(Customer.customer_id == customer_id,
                 Customer.marketplace == marketplace)).first()
        if not customer_obj:
            raise NotFoundError('Customer not found. Try different id')
        plan_obj = retrieve_plan(plan_id, marketplace, active_only=True)
        current_coupon = customer_obj.coupon
        start_date = datetime.now(UTC)
        due_on = datetime.now(UTC)
        coupon_use_count = customer_obj.coupon_use.get(current_coupon.coupon_id, 0)
        use_coupon = True if current_coupon.repeating == -1 or coupon_use_count \
                             <= current_coupon.repeating else False
        can_trial = True if customer_obj.plan_use.get(plan_obj.plan_id,
                                                      0) == 0 else False
        end_date = start_date + plan_obj.to_relativedelta(plan_obj.plan_interval)
        trial_interval = plan_obj.to_relativedelta(plan_obj.trial_interval)
        if can_trial:
            end_date += trial_interval
            due_on += trial_interval
        amount_base = plan_obj.price_cents
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
        invoice = ChargeInvoice(customer_id, marketplace, plan_id, coupon_id, start_date,
                                end_date, due_on, amount_base,
                                amount_after_coupon, amount_paid, balance)
        query_tool.add(invoice)
        customer_obj.coupon_use[coupon_id] += 1
        customer_obj.current_plan = plan_obj.plan_id
        prorate_last_invoice(customer_id, marketplace)
        query_tool.commit()
        #Todo send off task for due_on and sum the invoices that the balance


    def cancel_customer_plan(customer_id, marketplace, at_period_end=True):
        """
        Cancels a customers subscription. You can either do it immediately or
        at the end of the period.
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        :param at_period_end: Whether to cancel now or wait till the user
        :returns: New customer object.
        """
        customer = retrieve_customer(customer_id, marketplace)
        if at_period_end:
            #Todo schedule task that removes the plan at the end of the period,
            # make sure happens before renewal
            pass
        else:
            prorate_last_invoice(customer_id, marketplace)
            customer.current_plan = None
            customer.plan = None
        query_tool.commit()
        return customer


    def prorate_last_invoice(customer_id, marketplace):
        """
        Prorates the last invoice when changing a users plan. Only use when
        changing a users plan.
        :param customer_id: A unique id/uri for the customer
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        """
        right_now = datetime.now(UTC)
        last_invoice = query_tool.query(ChargeInvoice).filter(
            and_(ChargeInvoice.customer_id == customer_id,
                 ChargeInvoice.marketplace == marketplace,
                 ChargeInvoice.end_dt > right_now)).first()
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
        query_tool.flush()


    def change_customer_payout(customer_id, marketplace, payout_id,
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
        customer_obj = query_tool.query(Customer).filter(
            and_(Customer.customer_id == customer_id,
                 Customer.marketplace == marketplace)).first()
        if not customer_obj:
            raise NotFoundError('Customer not found. Try different id')
        payout_obj = retrieve_payout(payout_id, marketplace, active_only=True)
        now = datetime.now(UTC)
        first_charge = datetime.now(UTC)
        payout_amount = payout_obj.payout_amount_cents
        if not first_now:
            first_charge += payout_obj.to_relativedelta(payout_obj.payout_interval)
        if cancel_scheduled:
            query_tool.query(PayoutInvoice).filter(and_(PayoutInvoice.customer_id
                                                        == customer_id,
                                                        PayoutInvoice.marketplace
                                                        == marketplace,
                                                        PayoutInvoice.payout_date
                                                        > now))
        invoice = PayoutInvoice(customer_id, marketplace, payout_obj.payout_id,
                                first_charge, payout_amount, 0, payout_amount)
        customer_obj.current_payout = payout_obj.payout_id
        query_tool.add(invoice)
        #todo fire off task
        query_tool.commit()
        return customer_obj


    def cancel_customer_payout(customer_id, marketplace, cancel_scheduled=False):
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
        customer = retrieve_customer(customer_id, marketplace)
        if cancel_scheduled:
            query_tool.query(PayoutInvoice).filter(and_(PayoutInvoice.customer_id
                                                        == customer_id,
                                                        PayoutInvoice.marketplace
                                                        == marketplace,
                                                        PayoutInvoice.payout_date
                                                        > now))

        customer.current_payout = None
        query_tool.commit()
        return customer