from models import Customers
from billy.settings import query_tool
from sqlalchemy import and_
from billy.errors import NotFoundError, AlreadyExistsError
from datetime import datetime
from pytz import UTC
from billy.coupons.utils import retrieve_coupon
from billy.plans.utils import retrieve_plan

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

    #Retrieve customer's coupon
    #create an invoice
        #start_date = today
        #end_date = today + trial if first time + interval
        #due on = start_date + trial if first time
        #Fire off task to do on
    #prorate previous plan/close invoice
        #set previous invoice end_date to now
        #change amount due to negative if already paid



    #send off task for due_on and sum the invoices that the balance isn't zero
    pass

def cancel_customer_plan():
    #at period end/now
    #close previous invoice, handle balance
    pass