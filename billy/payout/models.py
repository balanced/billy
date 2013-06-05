from billy.models.base import Base, JSONDict
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from pytz import UTC
from datetime import datetime
from dateutil.relativedelta import relativedelta
from billy.errors import BadIntervalError
from billy.customer.models import Customer
from billy.errors import NotFoundError, AlreadyExistsError



class Payout(Base):
    __tablename__ = 'payouts'

    payout_id = Column(String, primary_key=True)
    marketplace = Column(String)
    name = Column(String)
    payout_amount_cents = Column(Integer)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    deleted_at = Column(DateTime(timezone=UTC))
    updated_at = Column(DateTime(timezone=UTC), default=datetime.now(UTC))
    payout_interval = Column(JSONDict)
    customers = relationship(Customer.__name__, backref='payouts')
    #Payout by percentage
    __table_args__ = (
    UniqueConstraint('payout_id', 'marketplace', name='payoutid_marketplace'),
    )


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
    def create_payout(cls, payout_id, marketplace, name, payout_amount_cents,
                      payout_interval):
        """
        Creates a payout that users can be assigned to.
        :param payout_id: A unique id/uri for the payout
        :param marketplace: a group/marketplace id/uri the user should be placed
        in (matches balanced payments marketplaces)
        :param name: A display name for the payout
        :param payout_amount_cents: Price in cents of the payout per interval. $1
        .00 = 100
        :param payout_interval: A Interval class that defines how frequently the
        make the payout
        :return: Payout Object if success or raises error if not
        :raise AlreadyExistsError: if payout already exists
        :raise TypeError: if intervals are not relativedelta (Interval class)
        """
        exists = cls.query.filter(
            cls.payout_id == payout_id, cls.marketplace == marketplace) \
            .first()
        if not exists:
            new_payout = Payout(
                payout_id = payout_id,
                marketplace = marketplace, name,
                                payout_amount_cents,
                                payout_interval)
            cls.session.add(new_payout)
            cls.session.commit()
            return new_payout
        else:
            raise AlreadyExistsError(
                'Payout already exists. Check payout_id and marketplace')

    @classmethod
    def retrieve_payout(cls, payout_id, marketplace, active_only=False):
        """
        This method retrieves a single payout.
        :param payout_id: the unique payout_id
        :param marketplace: the payouts marketplace/group
        :param active_only: if true only returns active payouts
        :raise NotFoundError:  if payout not found.
        """
        query = Payout.filter(Payout.payout_id == payout_id,
                              Payout.marketplace == marketplace)
        if active_only:

            query.filter(Payout.active == True)
        exists = query_tool.query(Payout).filter(and_filter).first()
        if not exists:
            raise NotFoundError(
                'Active Payout not found. Check payout_id and marketplace')
        return exists

    @classmethod
    def update_payout(cls, payout_id, marketplace, new_name):
        """
        Updates ONLY the payout name. By design the only updateable field is the
        name.
        To change other params create a new payout.
        :param payout_id: The payout id/uri
        :param marketplace: The group/marketplace id/uri
        :param new_name: The new display name for the payout
        :raise NotFoundError:  if payout not found.
        :returns: New Payout object
        """
        exists = query_tool.query(Payout).filter(
            and_(Payout.payout_id == payout_id, Payout.marketplace == marketplace)) \
            .first()
        if not exists:
            raise NotFoundError('Payout not found. Try different id')
        exists.name = new_name
        exists.updated_at = datetime.now(UTC)
        query_tool.commit()
        return exists

    @classmethod
    def list_payouts(cls, marketplace):
        #Todo active only
        """
        Returns a list of payouts currently in the database
        :param marketplace: The group/marketplace id/uri
        :returns: A list of Payout objects
        """
        results = query_tool.query(Payout).filter(
            Payout.marketplace == marketplace).all()
        return results


    def delete_payout(payout_id, marketplace):
        """
        This method deletes a payout. Payouts are not deleted from the database,
        but are instead marked as inactive so no new
        users can be added. Everyone currently on the payout is maintained on the
        payout.
        :param payout_id: the unique payout_id
        :param marketplace: the payout marketplace/group
        :returns: the deleted Payout object
        :raise NotFoundError:  if payout not found.
        """
        exists = query_tool.query(Payout).filter(
            and_(Payout.payout_id == payout_id, Payout.marketplace == marketplace)) \
            .first()
        if not exists:
            raise NotFoundError('Payout not found. Use different id')
        exists.active = False
        exists.updated_at = datetime.now(UTC)
        exists.deleted_at = datetime.now(UTC)
        query_tool.commit()
        return exists