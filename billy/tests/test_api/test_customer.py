from __future__ import unicode_literals

from api.resources import CustomerController, CustomerIndexController, \
    CouponIndexController
from . import BaseTestCase
from fixtures import (sample_customer, sample_customer_2, sample_customer_3,
                      sample_coupon)


class TestCustomers(BaseTestCase):
    schema = 'customer.json'
    controller = CustomerController
    index_controller = CustomerIndexController

    def setUp(self):
        super(TestCustomers, self).setUp()
        self.url_index = self.url_for(self.index_controller)
        self.url_single = lambda customer_id: self.url_for(self.controller,
                                                           customer_id=customer_id)


class TestCreateCustomer(TestCustomers):
    def test_create(self):
        # Simple valid creation test
        resp = self.client.post(self.url_index, user=self.test_users[0],
                                data=sample_customer)
        self.assertEqual(resp.status_code, 201)
        self.assertSchema(resp, self.schema)


    def test_create_bad_params(self):
        # Test bad customer_id
        data = sample_customer.copy()
        data['customer_id'] = None
        resp = self.client.post(self.url_index, user=self.test_users[0],
                                data=data)
        self.assertErrorMatches(resp, '400_CUSTOMER_ID')

        #Test bad provider id:
        data = sample_customer.copy()
        data['provider_id'] = None
        resp = self.client.post(self.url_index, user=self.test_users[0],
                                data=data)
        self.assertErrorMatches(resp, '400_PROVIDER_ID')

    def test_create_collision(self):
        self.client.post(self.url_index, user=self.test_users[0],
                         data=sample_customer)

        # Creating two customer under the same group with the same external id
        resp = self.client.post(self.url_index, user=self.test_users[0],
                                data=sample_customer)
        self.assertErrorMatches(resp, '409_CUSTOMER_ALREADY_EXISTS')

        # Create on different Group. Should work.
        resp = self.client.post(self.url_index, user=self.test_users[1],
                                data=sample_customer)
        self.assertEqual(resp.status_code, 201)


class TestGetCustomer(TestCustomers):
    def test_get(self):
        resp = self.client.post(self.url_index, user=self.test_users[0],
                                data=sample_customer)
        second_resp = self.client.get(
            self.url_single(sample_customer['customer_id']),
            user=self.test_users[0])

        # Make sure two responses match:
        self.assertEqual(resp.json(), second_resp.json())

        # Make sure second group can't retrieve first.
        resp = self.client.get(
            self.url_single(sample_customer['customer_id']),
            user=self.test_users[1])
        self.assertErrorMatches(resp, '404_CUSTOMER_NOT_FOUND')


    def test_get_list(self):
        self.client.post(self.url_index, user=self.test_users[0],
                         data=sample_customer)
        self.client.post(self.url_index, user=self.test_users[0],
                         data=sample_customer_2)
        self.client.post(self.url_index, user=self.test_users[1],
                         data=sample_customer_3)

        # Make sure group 1 only has 2 users
        resp = self.client.get(self.url_index, user=self.test_users[0])
        self.assertEqual(len(resp.json()), 2)
        for item in resp.json():
            self.assertSchema(item, self.schema)

        # Make sure group 2 only has 1 user
        resp = self.client.get(self.url_index, user=self.test_users[1])
        self.assertEqual(len(resp.json()), 1)
        for item in resp.json():
            self.assertSchema(item, self.schema)


class TestUpdate(TestCustomers):
    def test_update(self):
        # Create a customer
        self.client.post(self.url_index, user=self.test_users[0],
                         data=sample_customer)

        # Create a coupon
        coupon_url = self.url_for(CouponIndexController)
        resp = self.client.post(coupon_url, user=self.test_users[0],
                         data=sample_coupon)
        self.assertEqual(resp.status_code, 200)
        # Update with an existing coupon
        data = {'coupon_id': sample_coupon['coupon_id']}
        resp1 = self.client.put(self.url_single(sample_customer['customer_id']),
                               data=data,
                               user=self.test_users[0])
        self.assertEqual(resp1.status_code, 200)

        # Make sure the coupon is now attached:
        resp2 = self.client.get(self.url_single(sample_customer['customer_id']),
                               user=self.test_users[0])
        self.assertEqual(resp2.json()['current_coupon'],
                         sample_coupon['coupon_id'])

    def test_update_bad_params(self):
        self.client.post(self.url_index, user=self.test_users[0],
                         data=sample_customer)

        # Coupon DNE
        put_data = {'coupon_id': 'coupon_dne'}
        resp = self.client.put(
            self.url_single(sample_customer['customer_id']), data=put_data,
            user=self.test_users[0])
        self.assertErrorMatches(resp, '404_COUPON_NOT_FOUND')


        # Apply another groups coupon
        coupon_url = self.url_for(CouponIndexController)
        resp = self.client.post(coupon_url, user=self.test_users[1],
                         data=sample_coupon)
        self.assertEqual(resp.status_code, 200)
        data = {'coupon_id': sample_coupon['coupon_id']}
        resp1 = self.client.put(self.url_single(sample_customer['customer_id']),
                               data=data,
                               user=self.test_users[0])
        self.assertErrorMatches(resp1, '404_COUPON_NOT_FOUND')