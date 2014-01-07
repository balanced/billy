Getting started
===============

Billy has a set of simple REST API. It means that you can use your favorite 
programming language to call the API. By the time I am writing this,
there is a `Python API for Billy`_ is under development. If you are using
Python, you can use it instead of writing REST API calling by yourself.

.. _`Python API for Billy`: https://github.com/victorlin/billy-client

We will show you how to use Billy to process recurring payments for you in this 
section. If you want to know how to setup a Billy server, unfortunately, the
document is not available yet, but we will cover it later.

Register a company
------------------

Before you can use the Billy API, you need to register a company first. A 
company here is basically an user entity in the Billy system, there will be a 
corresponding API key generated and associated with the company entity. 
You will need to pass your API key in order to access any other API of the 
Billy server. As Billy's default payment processor is `Balanced Payments`_,
you will need to have an account and get a Balanced API key for registerion.

.. _`Balanced Payments`: https://balancedpayments.com

Okay, let's say your Balanced API key is `ef13dce2093b11e388de026ba7d31e6f`.
To register a company, here you call

::

    curl https://billing.balancedpayments.com/v1/companies/ -X POST \
        -d "processor_key=ef13dce2093b11e388de026ba7d31e6f"


and you should see the response

::

    {
        "guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "api_key": "6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb", 
        "created_at": "2013-10-02T05:29:43.953987", 
        "updated_at": "2013-10-02T05:29:43.953987"
    }

Currently, there is no easy way to retrive or reset the API key, so please do
not lost it. If you lost it, you can only contact the administrator to get it 
back. With the API key you get here, you can then call other API then.

Create a plan
-------------

A plan is a setup for recurring payment processing, it has the amount to 
charge or payout and the frequency of transaction. For instance, you are 
running a hosting service, you have three hosting plans

 * Small plan - 100GB storage, $5 USD/ mo
 * Middle plan - 200GB storage, $10 USD / mo
 * Large plan - 300GB storage, $15 USD / mo
 
Then you can create three corresponding plans in Billy system. Let's say, we 
want to create a Billy plan for the first hosting plan, then here we call

::

    curl https://billing.balancedpayments.com/v1/plans \
        -X POST \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "plan_type=charge" \
        -d "amount=500" \
        -d "frequency=monthly"


As we mentioned above, to call API other than the one for registering a 
company, you need to pass your API key, it's simple, all you need to do is
set it as the username for HTTP authentication. You want to charge your hosting
service customer periodically, so the `plan_type` is `charge` here. The price
for the plan is 5 USD dollars, but all amounts of Billy are in cents, so here 
you set the `amount` to `500`. And finally, it is a monthly plan, so you set the 
`frequency` to `monthly`.

Here we are, you should see the response

::

    {
        "guid": "PL97ZvyeA4wzM3WUyEG8xwps",
        "company_guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "plan_type": "charge", 
        "interval": 1, 
        "amount": 500, 
        "frequency": "monthly", 
        "deleted": false, 
        "created_at": "2013-10-02T05:48:26.210843", 
        "updated_at": "2013-10-02T05:48:26.210843"
    }

Create a customer
-----------------

A customer for Billy is the customer entity to your service, for example, a 
customer who subscribed your hosting plan. To create a customer, you can call
the API like this

::

   curl https://billing.balancedpayments.com/v1/customers \
       -X POST \
       -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: 

the response would be

::

    {
        "guid": "CUR1omRKGYYhqNaK1SyZqSbZ", 
        "company_guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "external_id": null, 
        "deleted": false, 
        "created_at": "2013-10-02T06:06:21.239505", 
        "updated_at": "2013-10-02T06:06:21.239505"
    }

When the Billy system is charging or paying out to the customer, a corresponding
customer entity will be created in Balanced. Sometimes, you just want to map 
the customer in Billy system to an existing customer in Balanced system, you 
can set the `external_id` parameter as the URI of customer in Balanced.

::

   curl https://billing.balancedpayments.com/v1/customers \
       -X POST \
       -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
       -d "external_id=/v1/customers/AC1jqOF9TocQXGIXjuMVrpMu"

Subscribe to a plan
-------------------

So far, you have a customer and a plan in the Billy system, however, at this 
moment, Billy have no idea what the funding source is. To subscribe the 
customer to the plan, you will need a `funding_instrument_uri` in Balanced system. In most 
cases, the `funding_instrument_uri` is a tokenlized credit card number or bank account. 
In this example, we use a tokenlized credit card number looks like this:

::

    /v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno

With that `funding_instrument_uri`, here we call

::

    curl https://billing.balancedpayments.com/v1/subscriptions \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "customer_guid=CUR1omRKGYYhqNaK1SyZqSbZ" \
        -d "plan_guid=PL97ZvyeA4wzM3WUyEG8xwps" \
        -d "funding_instrument_uri=/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno"

Then, here comes our subscription response:

::

    {
        "guid": "SUR6jKqqSyaFfGeeAsGaXFqZ",
        "plan_guid": "PL97ZvyeA4wzM3WUyEG8xwps", 
        "customer_guid": "CUR1omRKGYYhqNaK1SyZqSbZ", 
        "funding_instrument_uri": "/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno", 
        "period": 1, 
        "amount": null, 
        "canceled": false, 
        "canceled_at": null, 
        "started_at": "2013-10-02T06:35:00.380234", 
        "next_invoice_at": "2013-11-02T06:35:00.380234", 
        "created_at": "2013-10-02T06:35:00.380234", 
        "updated_at": "2013-10-02T06:35:00.380234", 
    }

Great! The Billy system just charged the credit card for you, and it will 
charge that credit card monthly afterward.

Subscribe with an overwritten amount
------------------------------------

In some cases, you may want to subscribe a customer to a plan with a 
different amount from the plan. For example, you want to give a discount
to one of your old customers. In this case, you can pass an optional parameter
`amount` to overwrite the amount from plan.

In the context of our hosting plan story, you want to give a 30% discount to 
an old customer, the original price is $5 USD, so the discounted amount would be
350 cents. Then here you can call

::

    curl https://billing.balancedpayments.com/v1/subscriptions \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "customer_guid=CUR1omRKGYYhqNaK1SyZqSbZ" \
        -d "plan_guid=PL97ZvyeA4wzM3WUyEG8xwps" \
        -d "funding_instrument_uri=/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno"
        -d "amount=350"

Schedule your subscription at a specific time
---------------------------------------------

By default, when you subscribe to a plan, the first transaction will be filed
and processed immediately. And transactions will appear in the same time of 
following days. For instance, if the `frequency` is `daily`, and you call the
API at 2013-01-01 7:10 AM, then the schedule will look like this

 * Transaction 1, at 2013-01-01 07:10 AM
 * Transaction 2, at 2013-01-02 07:10 AM
 * Transaction 3, at 2013-01-03 07:10 AM
 * ...

If the `frequency` is `monthly`, and the date is end of the month, the
closes day in that month will be used, for example, call the API at 
2013-01-30 7:00 AM, then the schedule will be

 * Transaction 1, at 2013-01-30 07:10 AM
 * Transaction 2, at 2013-02-28 07:10 AM
 * Transaction 3, at 2013-03-30 07:10 AM
 * ...

So, what if you want to schedule those transactions at a specific time rahter 
than the API calling time? It's simple, you can use the optional `started_at` 
parameter. For example, you have a violin course for beginners, to make things 
clear, you only want to collect your fee at 1st days of each month. The 
transaction schedule would look like this

 * Transaction 1, at 2013-01-01 00:00 AM
 * Transaction 2, at 2013-02-01 00:00 AM
 * Transaction 3, at 2013-03-01 00:00 AM
 * ...

In this case, to subscribe a student to your course plan, you can give it a 
`started_at` at the 1st of the next month. The `started_at` should be in ISO 
8601 format. Here is the call:


::

    curl https://billing.balancedpayments.com/v1/subscriptions \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "customer_guid=CUR1omRKGYYhqNaK1SyZqSbZ" \
        -d "plan_guid=PL97ZvyeA4wzM3WUyEG8xwps" \
        -d "funding_instrument_uri=/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno"
        -d "started_at=2013-10-01T00:00:00"

Cancel a subscription
---------------------

When a customer doesn't want to continue a subscription anymore, you will need
to cancel it. To cancel it, that's simple. For example, you want to cancel a
subscription `SUR6jKqqSyaFfGeeAsGaXFqZ`, then just call

::

    curl https://billing.balancedpayments.com/v1/subscriptions/SUR6jKqqSyaFfGeeAsGaXFqZ/cancel \
        -X POST \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

sometimes, you also want to issue a prorated refund when canceling the 
subscription. Let's say, there are 30 days from the latest transaction to 
the next transaction. And 10 days has already elapsed, you want to do a 
prorated refund to the customer for the rest 20 days. In this case, 
you can use `prorated_refund` parameter to let Billy do the refunding for you. 
Call it like this

::

    curl https://billing.balancedpayments.com/v1/subscriptions/SUR6jKqqSyaFfGeeAsGaXFqZ/cancel \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "prorated_refund=1"

If you want to refund an arbitrarity amount to the customer, you can use the
`refund_amount` parameter. For instance, you want to refund $5 USD to the 
customer, just call

::

    curl https://billing.balancedpayments.com/v1/subscriptions/SUR6jKqqSyaFfGeeAsGaXFqZ/cancel \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "refund_amount=500"

