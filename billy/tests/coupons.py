
from billy.models import Coupon
from billy.tests import BalancedTransactionalTestCase




class TestCoupon(BalancedTransactionalTestCase):

    def test_create_coupon(self):
        pass

    def test_create_and_retrieve(self):
        pass

    def test_retrieve_dne(self):
        pass

    def test_create_no_expire(self):
        #make sure it doesn't expire...
        pass

    def test_retrieve_params(self):
        pass

    def test_retrieve_active_only(self):
        pass

    def test_list_coupons(self):
        pass

    def test_list_coupons_active_only(self):
        pass

    def test_create_existing(self):
        pass

    def test_update(self):
        pass

    def test_update_classmethod(self):
        pass

    def test_delete(self):
        pass

    def test_delete_classmethod(self):
        pass

    def test_redeem_count(self):
        pass

    def test_expire_coupon(self):
        pass


    def test_expire_multiple(self):
        pass


    def test_max_redeem_validator(self):
        pass

    def test_repeating_validator(self):
        pass






