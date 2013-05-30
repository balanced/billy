from models import Customer
from billy.settings import query_tool
from sqlalchemy import and_
from billy.errors import NotFoundError, AlreadyExistsError, InactiveObjectError
from datetime import datetime
from pytz import UTC
from coupons import retrieve_coupon

def create_customer(customer_id, marketplace):
    """
    Creates a customer for the marketplace.
    :param customer_id: A unique id/uri for the customer
    :param marketplace: a group/marketplace id/uri the user should be placed in (matches balanced payments marketplaces)
    :return: Customer Object if success or raises error if not
    :raise AlreadyExistsError: if customer already exists
    """
    exists = query_tool.query(Customer).filter(and_(Customer.customer_id == customer_id, Customer.marketplace ==                                                                              marketplace)).first()
    if not exists:
        new_customer = Customer(customer_id, marketplace)
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
    exists = query_tool.query(Customer).filter(and_(Customer.customer_id == customer_id, Customer.marketplace == marketplace)).first()
    if not exists:
        raise NotFoundError('Customer not found. Check plan_id and marketplace')
    else:
        return exists

def list_all_customers(marketplace):
    """
    Returns a list of customers currently in the database
    :param marketplace: The group/marketplace id/uri
    :returns: A list of Customer objects
    """
    results = query_tool.query(Customer).filter(Customer.marketplace == marketplace).all()
    return results

def apply_coupon_to_customer(customer_id, marketplace, coupon_id):
    """
    Removes coupon associated with customer
    :param customer_id: A unique id/uri for the customer
    :param marketplace: a group/marketplace id/uri the user should be placed in (matches balanced payments marketplaces)
    :return: The new Customer object
    :raise NotFoundError: If customer not found
    """
    exists = query_tool.query(Customer).filter(and_(Customer.customer_id == customer_id, Customer.marketplace == marketplace)).first()
    if not exists:
        raise NotFoundError('Customer not found. Try different id')
    else:
        coupon_obj = retrieve_coupon(coupon_id, marketplace) #Raises NotFoundError if not found
        if coupon_obj.active:
            exists.current_coupon = coupon_id
            exists.updated_at = datetime.now(UTC)
            query_tool.commit()
            return exists
        else:
            raise InactiveObjectError("The Coupon is currently inactive and cant be applied.")

def remove_customer_coupon(customer_id, marketplace):
    """
    Removes coupon associated with customer
    :param customer_id: A unique id/uri for the customer
    :param marketplace: a group/marketplace id/uri the user should be placed in (matches balanced payments marketplaces)
    :return: The new Customer object
    :raise NotFoundError: If customer not found
    """
    exists = query_tool.query(Customer).filter(and_(Customer.customer_id == customer_id, Customer.marketplace == marketplace)).first()
    if not exists:
        raise NotFoundError('Customer not found. Try different id')
    if not exists.current_coupon:
        return exists
    else:
        exists.current_coupon = None
        exists.updated_at = datetime.now(UTC)
        query_tool.commit()
        return exists


def change_customer_plan(customer_id, marketplace, plan_id):
    #create an invoice
    #prorate previous plan/close invoice
    #send off task
    pass

def cancel_customer_plan():
    #at period end/now
    #close previous invoice, handle balance
    pass