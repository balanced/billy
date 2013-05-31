from models import Customers
from billy.settings import query_tool
from sqlalchemy import and_
from billy.errors import NotFoundError, AlreadyExistsError
from datetime import datetime
from pytz import UTC
from billy.coupons.utils import retrieve_coupon
from billy.plans.utils import retrieve_plan
from billy.invoices.models import Invoices
from decimal import Decimal

def create_customer(customer_id, marketplace):
    """
    Creates a customer for the marketplace.
    :param customer_id: A unique id/uri for the customer
    :param marketplace: a group/marketplace id/uri the user should be placed in (matches balanced payments marketplaces)
    :return: Customer Object if success or raises error if not
    :raise AlreadyExistsError: if customer already exists
    """
    exists = query_tool.query(Customers).filter(and_(Customers.customer_id == customer_id, Customers.marketplace ==                                                                              marketplace)).first()
    if not exists:
        new_customer = Customers(customer_id, marketplace)
        query_tool.add(new_customer)
        query_tool.commit()
        return new_customer
    else:
        raise AlreadyExistsError('Customer already exists. Check customer_id and marketplace')

def retrieve_customer(customer_id, marketplace):
    """
    This method retrieves a single plan.
    :param customer_id: A unique id/uri for the customer
    :param marketplace: a group/marketplace id/uri the user should be placed in (matches balanced payments marketplaces)
    :return: Customer Object if success or raises error if not
    :raise NotFoundError:  if plan not found.
    """
    #TODO: Retrieve FKeys with it
    exists = query_tool.query(Customers).filter(and_(Customers.customer_id == customer_id, Customers.marketplace == marketplace)).first()
    if not exists:
        raise NotFoundError('Customer not found. Check plan_id and marketplace')
    return exists

def list_all_customers(marketplace):
    """
    Returns a list of customers currently in the database
    :param marketplace: The group/marketplace id/uri
    :returns: A list of Customer objects
    """
    results = query_tool.query(Customers).filter(Customers.marketplace == marketplace).all()
    return results

def apply_coupon_to_customer(customer_id, marketplace, coupon_id):
    """
    Removes coupon associated with customer
    :param customer_id: A unique id/uri for the customer
    :param marketplace: a group/marketplace id/uri the user should be placed in (matches balanced payments marketplaces)
    :return: The new Customer object
    :raise NotFoundError: If customer not found
    """
    #Todo Increase use count disable if greater
    exists = query_tool.query(Customers).filter(and_(Customers.customer_id == customer_id, Customers.marketplace == marketplace)).first()
    if not exists:
        raise NotFoundError('Customer not found. Try different id')
    coupon_obj = retrieve_coupon(coupon_id, marketplace, active_only=True) #Raises NotFoundError if not found
    exists.current_coupon = coupon_id
    exists.updated_at = datetime.now(UTC)
    query_tool.commit()
    return exists

def remove_customer_coupon(customer_id, marketplace):
    """
    Removes coupon associated with customer
    :param customer_id: A unique id/uri for the customer
    :param marketplace: a group/marketplace id/uri the user should be placed in (matches balanced payments marketplaces)
    :return: The new Customer object
    :raise NotFoundError: If customer not found
    """
    #Todo reduce redeem count disable if less
    exists = query_tool.query(Customers).filter(and_(Customers.customer_id == customer_id, Customers.marketplace == marketplace)).first()
    if not exists:
        raise NotFoundError('Customer not found. Try different id')
    if not exists.current_coupon:
        return exists
    exists.current_coupon = None
    exists.updated_at = datetime.now(UTC)
    query_tool.commit()
    return exists


def change_customer_plan(customer_id, marketplace, plan_id):
    customer_obj = query_tool.query(Customers).filter(and_(Customers.customer_id == customer_id, Customers.marketplace == marketplace)).first()
    if not customer_obj:
        raise NotFoundError('Customer not found. Try different id')
    plan_obj = retrieve_plan(plan_id, marketplace, active_only=True)
    current_coupon = customer_obj.coupon
    start_date = datetime.now(UTC)
    due_on = datetime.now(UTC)
    coupon_use_count = customer_obj.coupon_use.get(current_coupon.coupon_id, 0)
    use_coupon = True if current_coupon.repeating == -1 or coupon_use_count <= current_coupon.repeating else False
    can_trial = True if customer_obj.plan_use.get(plan_obj.plan_id, 0) == 0 else False
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
        amount_after_coupon -= int(amount_after_coupon * Decimal(percent_off)/Decimal(100))
    invoice = Invoices(customer_id, marketplace, plan_id, coupon_id, start_date, end_date, due_on, amount_base,
                       amount_after_coupon, amount_paid, balance)
    query_tool.add(invoice)
    customer_obj.coupon_use[coupon_id] += 1
    exists = query_tool.query(Invoices).filter(and_(Invoices.customer_id == customer_id, Invoices.marketplace == marketplace, Invoices.end_dt > start_date)).first()
    if exists:
        time_total = Decimal((exists.end_dt - exists.due_dt).total_seconds())
        time_used = Decimal((exists.end_dt - start_date).total_seconds())
        percent_used = time_unused/time_total
        new_base = exists.amount_base_cents * per

        exists.end_dt = start_date
        exists.pri
    #prorate previous plan/close invoice
        #set previous invoice end_date to now
        #change amount due to negative if already paid



    #send off task for due_on and sum the invoices that the balance isn't zero
    query_tool.commit()


def cancel_customer_plan():
    #at period end/now
    #close previous invoice, handle balance
    pass