from __future__ import unicode_literals

from flask import request
from flask.ext.restful import marshal_with

from api.errors import BillyExc
from api.resources.group import GroupController
from models import Coupon
from form import CouponCreateForm, CouponUpdateForm
from view import coupon_view


class CouponIndexController(GroupController):
    """
    Base coupon resource used to create a coupon or retrieve all your
    coupons
    """

    @marshal_with(coupon_view)
    def get(self):
        """
        Return a list of coupon pertaining to a group
        """
        return self.group.coupons

    @marshal_with(coupon_view)
    def post(self):
        """
        Create a coupon
        """
        coupon_form = CouponCreateForm(request.form)
        if coupon_form.validate():
            return coupon_form.save(self.group)
        else:
            self.form_error(coupon_form.errors)


class CouponController(GroupController):
    """
    Methods pertaining to a single coupon
    """

    def __init__(self):
        super(CouponController, self).__init__()
        coupon_id = request.view_args.values()[0]
        self.coupon = Coupon.retrieve(coupon_id, self.group.guid)
        if not self.coupon:
            raise BillyExc['404_COUPON_NOT_FOUND']

    @marshal_with(coupon_view)
    def get(self, coupon_id):
        """
        Retrieve a single coupon
        """
        return self.coupon

    @marshal_with(coupon_view)
    def put(self, coupon_id):
        """
        Update a customer, currently limited to updating their coupon.
        """
        coupon_form = CouponUpdateForm(request.form)
        if coupon_form.validate():
            return coupon_form.save(self.coupon)

    def delete(self, coupon_id):
        """
        Deletes a coupon by marking it inactive. Does not effect users already
        on the coupon.
        """
        self.coupon.delete()
        return None



