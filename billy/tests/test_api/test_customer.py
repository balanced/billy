from __future__ import unicode_literals

from api.resources import CustomerController, CustomerIndexController
from . import BaseTestCase


class TestCustomers(BaseTestCase):
    good_customer = {
        'customer_id': 'MY_TEST_CUSTOMER',
        'provider_id': 'MY_DUMMY_PROVIDER'
    }
    schema = 'customer.json'
    controller = CustomerController
    index_controller = CustomerIndexController

    def setUp(self):
        super(TestCustomers, self).setUp()
        self.url_index = self.url_for(
            str(self.index_controller.__name__.lower()))
        self.url_single = lambda customer_id: self.url_for(
            str(self.controller.__name__.lower()), customer_id=customer_id)


class TestCreateCustomer(TestCustomers):
    def test_create(self):
        resp = self.client.post(self.url_index, user=self.test_users[0],
                                data=self.good_customer)
        self.assertEqual(resp.status_code, 200)
        self.check_schema(resp, self.schema)


    def test_create_bad_params(self):
        # TEST BAD customer_id
        pass
        customer = self.good_customer.copy()
        customer['customer_id'] = None


    def test_create_collision(self):
        pass


class TestGetCustomer(TestCustomers):
    def test_get(self):
        pass

    def test_get_list(self):
        pass


class TestUpdate(TestCustomers):
    def test_update(self):
        pass

    def test_update_bad_params(self):
        pass
