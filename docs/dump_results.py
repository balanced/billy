"""This script is for dumpping results from Billy server, so that we can paste
these to the document

"""
import sys

import balanced
from billy_client import BillyAPI
from billy_client import Plan

from billy.utils.generic import dumps_pretty_json


def dump_resource(output, title, resource):
    """Dump resource to output file

    """
    print >>output, '#' * 10, title
    print >>output
    print >>output, dumps_pretty_json(resource.json_data)
    print >>output


def main():
    balanced_key = 'ef13dce2093b11e388de026ba7d31e6f'
    mp_uri = '/v1/marketplaces/TEST-MP6lD3dBpta7OAXJsN766qA'
    endpoint = 'http://127.0.0.1:6543'

    balanced.configure(balanced_key)
    marketplace = balanced.Marketplace.find(mp_uri)
    # create a card to charge
    card = marketplace.create_card(
        name='BILLY_INTERGRATION_TESTER',
        card_number='5105105105105100',
        expiration_month='12',
        expiration_year='2020',
        security_code='123',
    )

    api = BillyAPI(None, endpoint=endpoint)
    company = api.create_company(processor_key=balanced_key)
    api_key = company.api_key

    api = BillyAPI(api_key, endpoint=endpoint)
    customer = company.create_customer()
    plan = company.create_plan(
        plan_type=Plan.TYPE_DEBIT,
        frequency=Plan.FREQ_MONTHLY,
        amount=500,
    )
    subscription = plan.subscribe(
        customer_guid=customer.guid,
        funding_instrument_uri=card.uri,
    )
    invoice = customer.invoice(
        amount=1000,
        appears_on_statement_as='FooBar Hosting',
        items=[
            dict(name='Hosting Service A', amount=1000),
        ],
        adjustments=[
            dict(amount=-100, reason='Coupon discount')
        ]
    )

    with open(sys.argv[1], 'wt') as output:
        dump_resource(output, 'Company', company)
        dump_resource(output, 'Customer', customer)
        dump_resource(output, 'Plan', plan)
        dump_resource(output, 'Subscription', subscription)
        dump_resource(output, 'Invoice', invoice)
        dump_resource(output, 'Transaction', list(subscription.list_transactions())[0])

    # TODO: we should integrate this response getting process into something
    # like document template generating tool. Ohterwise it's really hateful
    # and time consuming, also error prone to do this copy paste and modify
    # manually


if __name__ == '__main__':
    main()
