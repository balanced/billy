Getting started
===============

Billy has a set of simple REST API. It means that you can use your favorite 
programming language to call the API. By the time I am writing this,
there is a `Python API for Billy`_ is under development. If you are using
Python, you can use it instead of writing REST API calling by yourself.

.. _`Python API for Billy`: https://github.com/victorlin/billy-client

We will show you how to use Billy to process recurring payments for you in this 
section. If you want to know how to setup a Billy server, unfortunately, this
document doesn't cover that part yet.

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

Currently, there is no easy way to Retrieve or reset the API key, so please do
not lost it. If you lost it, you can only contact the administrator to get it 
back. 

Create a plan
-------------

A plan is a configuration for recurring payment processing, it contains the 
amount to charge or payout and the frequency of payment processing. For 
instance, you are running a hosting business, you have three hosting service 
types:

 * Small plan - 100GB storage, $5 USD/ mo
 * Middle plan - 200GB storage, $10 USD / mo
 * Large plan - 300GB storage, $15 USD / mo
 
To charge your customer montly, you can create three plan entities in Billy 
system correspond to your three hosting service types. Here we demonstrate 
how to create a Billy plan for your first hosting type:

::

    curl https://billing.balancedpayments.com/v1/plans \
        -X POST \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "plan_type=charge" \
        -d "amount=500" \
        -d "frequency=monthly"


As we mentioned above, to call any API other than the one for registering a 
company, you need to pass your API key, it's easy, all you need to do is
set it as the username for HTTP authentication. As you want to charge your 
hosting service customers rather than paying them out, the `plan_type` is `charge` 
here. The price for the plan is 5 USD dollars, but as the money unit in Billy 
system are all in cents, so here you set the `amount` to `500`. And finally, 
it is a monthly charge, so you set the `frequency` to `monthly`.

Here we are, you should see the response looks like this one:

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

When you have a new customer who wants to subscribe your hosting service,
you need to create a customer entity in Billy system for him. To create 
a customer, you can call the API like this:

::

   curl https://billing.balancedpayments.com/v1/customers \
       -X POST \
       -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: 

and the response would be

::

    {
        "guid": "CUR1omRKGYYhqNaK1SyZqSbZ", 
        "company_guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "processor_uri": null, 
        "deleted": false, 
        "created_at": "2013-10-02T06:06:21.239505", 
        "updated_at": "2013-10-02T06:06:21.239505"
    }

Before Billy system charging or paying out to the customer, a corresponding
customer entity will be created in Balanced. Sometimes, you want to map 
the customer in Billy system to an existing customer in Balanced system, you 
can set the `processor_uri` parameter as the URI of customer in Balanced.

::

   curl https://billing.balancedpayments.com/v1/customers \
       -X POST \
       -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
       -d "processor_uri=/v1/customers/AC1jqOF9TocQXGIXjuMVrpMu"


.. note::

    As the name `processor_uri` implies, it **MUST** be the URI to a Balanced
    customer rahter than its GUID.  


Subscribe to a plan
-------------------

So far so good, you have a customer and a plan in the Billy system, however, 
before you can subscribe the customer to the plan, you will need a 
funding source in Balanced system to charge. In most cases, the 
funding source is a tokenlized credit card number or a bank account. 
In this example, we use a tokenlized credit card number looks like this:

::

    /v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno

For how to generate a tokenlized credit card number, you can reference to the
`Balanced documents here`_.

.. _`Balanced documents here`: https://docs.balancedpayments.com/current/api.html?language=bash#tokenize-a-card

With that funding source, to subscribe the customer to our plan, here we call

::

    curl https://billing.balancedpayments.com/v1/subscriptions \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "customer_guid=CUR1omRKGYYhqNaK1SyZqSbZ" \
        -d "plan_guid=PL97ZvyeA4wzM3WUyEG8xwps" \
        -d "funding_instrument_uri=/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno"

Then, here comes the subscription response:

::

    {
        "guid": "SUR6jKqqSyaFfGeeAsGaXFqZ",
        "plan_guid": "PL97ZvyeA4wzM3WUyEG8xwps", 
        "customer_guid": "CUR1omRKGYYhqNaK1SyZqSbZ", 
        "funding_instrument_uri": "/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno", 
        "invoice_count": 1, 
        "amount": null, 
        "appears_on_statement_as": null,
        "canceled": false, 
        "canceled_at": null, 
        "started_at": "2013-10-02T06:35:00.380234", 
        "next_invoice_at": "2013-11-02T06:35:00.380234", 
        "created_at": "2013-10-02T06:35:00.380234", 
        "updated_at": "2013-10-02T06:35:00.380234", 
    }

Congratulations! The Billy system just generated an invoice and charged the 
credit card for you, and it will generate invoices and try to charge that credit 
card monthly afterward. To view your invoices, you can visit 

::
    
    /v1/subscriptions/<Subscription GUID/invoices

with your API key like this

::

    curl https://billing.balancedpayments.com/v1/subscriptions/SUR6jKqqSyaFfGeeAsGaXFqZ/invoices \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

and here is the response

::

    {
        "items": [
            {
                "adjustments": [],
                "amount": 500,
                "appears_on_statement_as": null,
                "created_at": "2013-10-02T06:35:00.380234",
                "effective_amount": 500,
                "funding_instrument_uri": null,
                "guid": "IVFRvtNxGvoWMehPG63Uyz1X",
                "invoice_type": "subscription",
                "items": [],
                "scheduled_at": "2013-10-02T06:35:00.380234",
                "status": "init",
                "subscription_guid": "SUR6jKqqSyaFfGeeAsGaXFqZ",
                "title": null,
                "total_adjustment_amount": 0,
                "transaction_type": "charge",
                "updated_at": "2013-10-02T06:35:00.380234"
            }
        ],
        "limit": 20,
        "offset": 0
    }

Subscribe with an overwritten amount
------------------------------------

In some cases, you may want to subscribe a customer to a plan with a 
different amount from the plan. For example, you want to give a discount
to one of your old customers. In this case, you can pass an optional parameter
`amount` to overwrite the amount from plan.

In the context of our hosting business story, you want to give a 30% discount to 
the old customer, the original price is $5 USD, then discounted amount would be
350 cents, so here you can call

::

    curl https://billing.balancedpayments.com/v1/subscriptions \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "customer_guid=CUR1omRKGYYhqNaK1SyZqSbZ" \
        -d "plan_guid=PL97ZvyeA4wzM3WUyEG8xwps" \
        -d "funding_instrument_uri=/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno"
        -d "amount=350"

Schedule your subscription at a specific time
---------------------------------------------

By default, when you subscribe to a plan, the first invoice will be filed
and processed immediately. Then all following invoices will appear in the same 
time of following days. For instance, if the `frequency` is `daily`, and you call the
API at 2013-01-01 7:10 AM, then the schedule will look like this

 * Invoice 1, at 2013-01-01 07:10 AM
 * Invoice 2, at 2013-01-02 07:10 AM
 * Invoice 3, at 2013-01-03 07:10 AM
 * ...

If the `frequency` is `monthly`, and the begin date is the last day of a month, 
then Billy will pick the closest day in following months, for example, we call 
the API at 2013-01-30 7:00 AM, then the schedule for invoices will be

 * Invoice 1, at 2013-01-30 07:10 AM
 * Invoice 2, at 2013-02-28 07:10 AM
 * Invoice 3, at 2013-03-30 07:10 AM
 * ...

So, what if you want to schedule those transactions at a specific time rather
than the API calling time? It's simple, you can use the optional `started_at` 
parameter. For example, you have a violin course for beginners, to make things 
clear, you want to collect your fee only at the first day of all months. The 
invoice schedule would look like this

 * Invoice 1, at 2013-01-01 00:00 AM
 * Invoice 2, at 2013-02-01 00:00 AM
 * Invoice 3, at 2013-03-01 00:00 AM
 * ...

In this case, to subscribe a new student to your course plan, you can give it a 
`started_at` at the 1st of the next month. The `started_at` should be in ISO 
8601 format. Here is our call:

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
to cancel it. To cancel it, that's easy. For example, you want to cancel a
subscription `SUR6jKqqSyaFfGeeAsGaXFqZ`, then just call

::

    curl https://billing.balancedpayments.com/v1/subscriptions/SUR6jKqqSyaFfGeeAsGaXFqZ/cancel \
        -X POST \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Refund an invoice
-----------------

Sometimes, you may want to issue a refund to customer, here you can call:

::

    curl https://billing.balancedpayments.com/v1/invoices/IVFRvtNxGvoWMehPG63Uyz1X/refund \
        -X POST \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "amount=100"
