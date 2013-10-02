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

.. _`Balanced Payments`: http://balancedpayments.com

Okay, let's say your Balanced API key is `ef13dce2093b11e388de026ba7d31e6f`.
To register a company, here you call

::

    curl http://billing.balancedpayments.com/v1/companies/ -X POST \
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

    curl http://billing.balancedpayments.com/v1/plans \
        -X POST \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "plan_type=charge" \
        -d "amount=5" \
        -d "frequency=monthly"


As we mentioned above, to call API other than the one for registering a 
company, you need to pass your API key, it's simple, all you need to do is
set it as the username for HTTP authentication. You want to charge your hosting
service customer periodically, so the `plan_type` is `charge` here. The price
for the plan is 5 USD dollars, so here you set the `amount` to `5`. And 
finally, it is a monthly plan, so you set the `frequency` to `monthly`.

Here we are, you should see the response

::

    {
        "guid": "PL97ZvyeA4wzM3WUyEG8xwps",
        "company_guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "plan_type": "charge", 
        "interval": 1, 
        "amount": "5.00", 
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

   curl http://billing.balancedpayments.com/v1/customers \
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

   curl http://billing.balancedpayments.com/v1/customers \
       -X POST \
       -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
       -d "external_id=/v1/customers/AC1jqOF9TocQXGIXjuMVrpMu"

Subscribe to a plan
-------------------

So far, you have a customer and a plan in the Billy system, however, at this 
moment, Billy have no idea what the funding source is. To subscribe the 
customer to the plan, you will need a `payment_uri` in Balanced system. In most 
cases, the `payment_uri` is a tokenlized credit card number or bank account. 
In this example, we use a tokenlized credit card number looks like this:

::

    /v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno

With that `payment_uri`, here we call

::

    curl http://billing.balancedpayments.com/v1/subscriptions \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "customer_guid=CUR1omRKGYYhqNaK1SyZqSbZ" \
        -d "plan_guid=PL97ZvyeA4wzM3WUyEG8xwps" \
        -d "payment_uri=/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno"

Then, here comes our subscription response:

::

    {
        "guid": "SUR6jKqqSyaFfGeeAsGaXFqZ",
        "plan_guid": "PL97ZvyeA4wzM3WUyEG8xwps", 
        "customer_guid": "CUR1omRKGYYhqNaK1SyZqSbZ", 
        "payment_uri": "/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno", 
        "period": 1, 
        "amount": null, 
        "canceled": false, 
        "canceled_at": null, 
        "started_at": "2013-10-02T06:35:00.380234", 
        "next_transaction_at": "2013-11-02T06:35:00.380234", 
        "created_at": "2013-10-02T06:35:00.380234", 
        "updated_at": "2013-10-02T06:35:00.380234", 
    }

Great! The Billy system just charged the credit card for you, and it will 
charge that credit card monthly afterward.

Cancel the subscription
-----------------------

TODO:

