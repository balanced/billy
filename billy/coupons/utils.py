from billy.errors import NotFoundError, AlreadyExistsError
from billy.coupons.models import Coupon
from billy.settings import query_tool
from sqlalchemy import and_
from datetime import datetime
from pytz import UTC

def create_coupon(coupon_id, marketplace, name, price_off_cents, percent_off_int, expire, max_redeem, repeating):
    """
    Creates a coupon that can be later applied to a customer.
    :param coupon_id: A unique id for the coupon
    :param marketplace: The marketplace/group uri/id this coupon is associated with
    :param name: A display name for the coupon
    :param price_off_cents: In CENTS the $ amount off on each invoice. $1.00 == 100
    :param percent_off_int: The percent to reduce off each invoice. 25% == 25
    :param expire: Datetime in which after the coupon will no longer work
    :param max_redeem: The number of unique users that can redeem this coupon
    :param repeating: The maximum number of invoices it applies to. -1 for all/forver
    :return: The new coupon object
    :raise AlreadyExistsError: If the coupon already exists
    """
    exists = query_tool.query(Coupon).filter(and_(Coupon.coupon_id == coupon_id, Coupon.marketplace == marketplace)).first()
    if not exists:
        new_coupon = Coupon(coupon_id, marketplace, name, price_off_cents, percent_off_int, expire, max_redeem, repeating)
        query_tool.add(new_coupon)
        query_tool.commit()
        return new_coupon
    else:
        raise AlreadyExistsError('Coupon already exists. Check coupon_id and marketplace')


def retrieve_coupon(coupon_id, marketplace, active_only=False):
    """
    This method retrieves a single coupon.
    :param coupon_id: the unique coupon_id
    :param marketplace: the coupon marketplace/group
    :param active_only: only returns active coupons
    :returns: Single coupon
    :raise NotFoundError:  if coupon not found.
    """
    if active_only:
        and_filter = and_(Coupon.coupon_id == coupon_id, Coupon.marketplace == marketplace, Coupon.active == True)
    else:
        and_filter = and_(Coupon.coupon_id == coupon_id, Coupon.marketplace == marketplace)
    exists = query_tool.query(Coupon).filter(and_filter).first()
    if not exists:
        raise NotFoundError('Active Coupon not found. Check coupon_id and marketplace')
    return exists


def update_coupon(coupon_id, marketplace, new_name=None, new_max_redeem=None, new_expire=None, new_repeating=None):
    """
    Updates the coupon information, by design only the params listed are updatable and
    effect future charges.
    :param coupon_id: A unique id for the coupon
    :param marketplace: The marketplace/group uri/id this coupon is associated with
    :param new_name: A display name for the coupon
    :param new_max_redeem: The number of unique users that can redeem this coupon
    :param new_expire: Datetime in which after the coupon will no longer work
    :param new_repeating: The maximum number of invoices it applies to. -1 for all/forever
    :raise NotFoundError:  if coupon not found.
    :returns: New coupon object
    """
    #Todo update active if max_redeem below/above times_used
    exists = query_tool.query(Coupon).filter(and_(Coupon.coupon_id == coupon_id, Coupon.marketplace == marketplace)).first()
    if not exists:
        raise NotFoundError('Coupon not found. Use different id/marketplace')
    else:
        if new_name:
            exists.name = new_name
        if new_max_redeem:
            exists.max_redeem = new_max_redeem
        if new_expire:
            exists.expire = new_expire
        if new_repeating:
            exists.repeating = new_repeating
        exists.updated_at = datetime.now(UTC)
        query_tool.commit()
        return exists

def delete_coupon(coupon_id, marketplace):
    """
    This method deletes a coupon. Coupons are not deleted from the database, but are instead marked as inactive so no
    new users can be added. Everyone currently on the plan
    :param coupon_id: the unique coupon_id
    :param marketplace: the plans marketplace/group
    :returns: the deleted Coupon object
    :raise NotFoundError:  if coupon not found.
    """
    exists = query_tool.query(Coupon).filter(and_(Coupon.coupon_id == coupon_id, Coupon.marketplace == marketplace)).first()
    if not exists:
        raise NotFoundError('Coupon not found. Try a different id')
    exists.active = False
    exists.updated_at = datetime.now(UTC)
    exists.deleted_at = datetime.now(UTC)
    query_tool.commit()
    return exists

def list_coupons(marketplace):
    #Todo active only
    """
    Returns a list of coupons currently in the database
    :param marketplace: The group/marketplace id/uri
    :returns: A list of Coupon objects
    """
    results = query_tool.query(Coupon).filter(Coupon.marketplace == marketplace).all()
    return results