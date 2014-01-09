REST API reference
==================

The official endpoint of Billy API is

::

    https://billing.balancedpayments.com

When you found a bug, or you have any suggestion to this project, please create 
an issue in our `GitHub repo`_.


.. _`GitHub repo`: https://github.com/balanced/billy

All HTTP responses except errors will be in JSON format. Other format is not 
supported currently. To access the API, you need an API key, except the one for 
registering a company. The API key should be passed as the username for 
`HTTP basic authentication`_, leave the password blank.

.. _`HTTP basic authentication`: http://en.wikipedia.org/wiki/Basic_access_authentication


Company
-------

A company is an user account for using the Billy system, you need to pass your 
Balanced API key to create one, so that Billy can process payments via Balanced 
for you. Company has a generated API key which is required for performing any 
further operations in Billy system. 

.. note::

    You **MUST** keep these API keys as **secret**, do not share them with 
    anyone, do not post them on IRC. Also, currently, Billy API key cannot be 
    Retrieved or reset easily, if you lost it, you can only contact 
    administrator to ask them reset it for you.

Create
~~~~~~

Create a company and return the entity. Only this method does not require an
API key to access as you need it to generate one. Remember to save the API key
in response.

Method
    POST
Endpoint
    /v1/companies
Parameters
    - **processor_key** - The API key for your Balanced account

Example:

::

    curl https://billing.balancedpayments.com/v1/companies \
        -X POST \
        -d "processor_key=ef13dce2093b11e388de026ba7d31e6f"

Response:

::

    {
        "guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "api_key": "6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb", 
        "created_at": "2013-10-02T05:29:43.953987", 
        "updated_at": "2013-10-02T05:29:43.953987"
    }

Retrieve
~~~~~~~~

Retrieve a company record

Method
    GET
Endpoint
    /v1/companies/<Company GUID>

Example:

::

    curl https://billing.balancedpayments.com/v1/companies/CPMM8C8Uhkt4pDeJ8oqJu8Nj \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "api_key": "6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb", 
        "created_at": "2013-10-02T05:29:43.953987", 
        "updated_at": "2013-10-02T05:29:43.953987"
    }

Plan
----

A plan is a setup for recurring charing or paying out, it contains the amount to 
charge or payout and the frequency of generating invoices.

Create
~~~~~~

Create a plan and return the entity.

Method
    POST
Endpoint
    /v1/plans
Parameters
    - **plan_type** - The type of this plan can be either **charge** for 
      charging customer or **payout** for paying out.
    - **frequency** - The frequency to schedule charging or paying out to 
      customer. Can be one of

      - daily
      - weekly
      - monthly
      - yearly

      When it is **monthly** and the schedule started at the end of a month, the 
      closest day to the started one in a month will be selected for following 
      invoices. For example, the started date time is 2013-01-30, then 
      following invoices will occur at 2013-02-28, 2013-03-30 and so on.

    - **amount** - The amount in USD cents to charge or payout to customer
    - **interval** - (optional) The interval of frequency period to multiply, 
      the default value is 1. For example, to charge or payout a customer
      by two weeks frequency, you can set the frequency to **weekly**, and set
      the **interval** to 2, then the schedule will be in a biweekly manner.


Example:

::

    curl https://billing.balancedpayments.com/v1/plans \
        -X POST \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "plan_type=charge" \
        -d "amount=500" \
        -d "frequency=monthly"

Response:

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

Retrieve
~~~~~~~~

Retrieve a plan entity

Method
    GET
Endpoint
    /v1/plans/<Plan GUID>

Example:

::

    curl https://billing.balancedpayments.com/v1/plans/PL97ZvyeA4wzM3WUyEG8xwps \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

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

Delete
~~~~~~

Delete a plan and return entity.

Method
    DELETE
Endpoint
    /v1/plans/<Plan GUID>

Example:

::

    curl https://billing.balancedpayments.com/v1/plans/PL97ZvyeA4wzM3WUyEG8xwps \
        -X DELETE \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "guid": "PL97ZvyeA4wzM3WUyEG8xwps",
        "company_guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "plan_type": "charge", 
        "interval": 1, 
        "amount": 500, 
        "frequency": "monthly", 
        "deleted": true, 
        "created_at": "2013-10-02T05:48:26.210843", 
        "updated_at": "2013-10-02T05:48:26.210843"
    }

List
~~~~

List all plans

Method
    GET
Endpoint
    /v1/plans
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20

Example:

::

    curl https://billing.balancedpayments.com/v1/plans \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "items": [
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
        ], 
        "limit": 20, 
        "offset": 0
    }

List customers
~~~~~~~~~~~~~~

List all customers who subscripted to the plan

Method
    GET
Endpoint
    /v1/plans/<Plan GUID/customers
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20


List subscriptions
~~~~~~~~~~~~~~~~~~

List all subscriptions owned by the plan

Method
    GET
Endpoint
    /v1/plans/<Plan GUID/subscriptions
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20


List invoices
~~~~~~~~~~~~~

List all invoices generated by subscriptions owned by the plan

Method
    GET
Endpoint
    /v1/plans/<Plan GUID/invoices
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20

List transactions
~~~~~~~~~~~~~~~~~

List all transactions generated by subscriptions owned by the plan

Method
    GET
Endpoint
    /v1/plans/<Plan GUID/transactions
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20

Customer
--------

An entity for customer to your service. Before the first time of charging or 
paying out, a corresponding `customer record in Balanced`_ system will be 
created. If you want to map an existing customer in Balanced, you can set the 
`processor_uri` to the URI of customer in balanced.

.. _`customer record in Balanced`: https://docs.balancedpayments.com/current/api.html?language=bash#customers


Create
~~~~~~

Create a customer and return the record. 

Method
    POST
Endpoint
    /v1/customers
Parameters
    - **processor_uri** - (optional) The URI to an existing customer record in
      Balanced server

Example:

::

   curl https://billing.balancedpayments.com/v1/customers \
       -X POST \
       -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: 

Response:

::

    {
        "guid": "CUR1omRKGYYhqNaK1SyZqSbZ", 
        "company_guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "processor_uri": null, 
        "deleted": false, 
        "created_at": "2013-10-02T06:06:21.239505", 
        "updated_at": "2013-10-02T06:06:21.239505"
    }

Retrieve
~~~~~~~~

Retrieve a customer entity

Method
    GET
Endpoint
    /v1/customers/<Customer GUID>

Example:

::

    curl https://billing.balancedpayments.com/v1/customers/CUR1omRKGYYhqNaK1SyZqSbZ \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "guid": "CUR1omRKGYYhqNaK1SyZqSbZ", 
        "company_guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "processor_uri": null, 
        "deleted": false, 
        "created_at": "2013-10-02T06:06:21.239505", 
        "updated_at": "2013-10-02T06:06:21.239505"
    }

Delete
~~~~~~

Delete a customer and return entity.

Method
    DELETE
Endpoint
    /v1/customers/<Customer GUID>

Example:

::

    curl https://billing.balancedpayments.com/v1/customers/CUR1omRKGYYhqNaK1SyZqSbZ \
        -X DELETE \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "guid": "CUR1omRKGYYhqNaK1SyZqSbZ", 
        "company_guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "processor_uri": null, 
        "deleted": true, 
        "created_at": "2013-10-02T06:06:21.239505", 
        "updated_at": "2013-10-02T06:06:21.239505"
    }

List
~~~~

List all customers

Method
    GET
Endpoint
    /v1/customers
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20

Example:

::

    curl https://billing.balancedpayments.com/v1/customers \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "items": [
            {
                "guid": "CUR1omRKGYYhqNaK1SyZqSbZ", 
                "company_guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
                "processor_uri": null, 
                "deleted": false, 
                "created_at": "2013-10-02T06:06:21.239505", 
                "updated_at": "2013-10-02T06:06:21.239505"
            }
        ], 
        "limit": 20, 
        "offset": 0
    }

List subscriptions
~~~~~~~~~~~~~~~~~~

List all subscriptions owned by the customer

Method
    GET
Endpoint
    /v1/customers/<Customer GUID/subscriptions
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20

List invoices
~~~~~~~~~~~~~

List all invoices owned by the customer

Method
    GET
Endpoint
    /v1/customers/<Customer GUID/invoices
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20

List transactions
~~~~~~~~~~~~~~~~~

List all transactions owned by the customer

Method
    GET
Endpoint
    /v1/customers/<Customer GUID/transactions
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20


Subscription
------------

An entity of subscription relationship between customer and plan. Invoices
will be generated for the customer automatically and periodically according to 
the configuration of plan.

Create
~~~~~~

Create a subscription and return the entity. If the **funding_instrument_uri** 
is given, it will be used to charge or payout to customer, however, if it is 
omitted, an invoice without `funding_instrument_uri` will be generated.
You can update the `funding_instrument_uri` of invoice later. This allows you 
to generate invoice without knowing `funding_instrument_uri` at first, 
defer the fee collection later. If **started_at** is given, the subscription 
will be scheduled at that date time, otherwise, current time will be the 
started time, also, an invoice will be filed immediately.

Method
    POST
Endpoint
    /v1/subscriptions
Parameters
    - **plan_guid** - The GUID of plan to subscribe 
    - **customer_guid** - The GUID of customer to subscribe
    - **funding_instrument_uri** - (optional) The URI to funding source in Balanced, 
      could be a tokenlized credit card or bank account URI
    - **amount** - (optional) The amount in USD cents of this subscription for 
      overwriting the one from plan, useful for giving a discount to customer
    - **started_at** - (optional) The date time of this subscription to started
      at, should be in ISO 8601 format.
    - **appears_on_statement_as** - (optional) The statement to appears on 
      customer's credit card or bank account transaction record

Example:

::

    curl https://billing.balancedpayments.com/v1/subscriptions \
        -X POST \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "customer_guid=CUR1omRKGYYhqNaK1SyZqSbZ" \
        -d "plan_guid=PL97ZvyeA4wzM3WUyEG8xwps" \
        -d "funding_instrument_uri=/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno"

Response:

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

Retrieve
~~~~~~~~

Retrieve a subscription entity

Method
    GET
Endpoint
    /v1/subscriptions/<Subscription GUID>

Example:

::

    curl https://billing.balancedpayments.com/v1/subscriptions/SUR6jKqqSyaFfGeeAsGaXFqZ \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

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

Cancel
~~~~~~

Cancel the subscription.

Method
    POST
Endpoint
    /v1/subscriptions/<Subscription GUID>/cancel

Example:

::

    curl https://billing.balancedpayments.com/v1/subscriptions/SUR6jKqqSyaFfGeeAsGaXFqZ/cancel \
        -X POST
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "guid": "SUR6jKqqSyaFfGeeAsGaXFqZ",
        "plan_guid": "PL97ZvyeA4wzM3WUyEG8xwps", 
        "customer_guid": "CUR1omRKGYYhqNaK1SyZqSbZ", 
        "funding_instrument_uri": "/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno", 
        "invoice_count": 1, 
        "amount": null, 
        "appears_on_statement_as": null,
        "canceled": true, 
        "canceled_at": "2013-10-03T12:16:00.532295", 
        "started_at": "2013-10-02T06:35:00.380234", 
        "next_invoice_at": "2013-11-02T06:35:00.380234", 
        "created_at": "2013-10-02T06:35:00.380234", 
        "updated_at": "2013-10-02T06:35:00.380234", 
    }

List
~~~~

List all subscriptions

Method
    GET
Endpoint
    /v1/subscriptions
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20

Example:

::

    curl https://billing.balancedpayments.com/v1/subscriptions \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "items": [
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
        ], 
        "limit": 20, 
        "offset": 0
    }

List invoices
~~~~~~~~~~~~~~~~~

List all invoices owned by the subscription

Method
    GET
Endpoint
    /v1/subscriptions/<Subscription GUID/invoices
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20


List transactions
~~~~~~~~~~~~~~~~~

List all transactions generated from invoices owned by the subscription

Method
    GET
Endpoint
    /v1/subscriptions/<Subscription GUID/transactions
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20


Invoice
-------

An invoice is an entity generated from a subscription periodically, or 
generated for a customer direcly. You should notice that when the plan of 
subscription is a payout plan, invoice will also be generated.


Create
~~~~~~

Create an invoice for a customer and return the entity. 

Method
    POST
Endpoint
    /v1/invoices
Parameters
    - **customer_guid** - The guid of customer
    - **amount** - The amount to charge customer
    - **title** - (optional) The title of this invoice
    - **appears_on_statement_as** - (optional) The statement to appears on 
      customer's credit card or bank account transaction record
    - **funding_instrument_uri** - (optional) The URI to Balanced funding
      instrument to charge
    - **items** - (optional) The items which indicate service or goods to 
      charge. Fields of an item:

      - **name** - The name of item
      - **amount** - The amount of item (will not affect invoice amount)
      - **type** - (optional) The type of item (a short string), e.g. `Bandwidth`
      - **quanity** - (optional) The quantity of item
      - **volume** - (optional) The volume of item
      - **unit** - (optional) The unit of item

      The parameter key format is `item_<field name><number>`. For example,
      you have two items, hosting service A and hosting service B, then
      you can pass these two items with following key/value pairs of 
      parameters

      - item_name1=Hosting Service A
      - item_amount1=1000
      - item_name2=Hosting Service B
      - item_amount2=3000

    - **adjustments** - (optional) The adjustments to be applied on this 
      invoice. You should notice that **adjustments will affect the effective
      amount of an invoice.** It is useful for discounts or extra fee.
      There are only two fields for an adjustment:

      - **amount** - The adjustment amount (will affect invoice effective amount)
      - **reason** - (optional) The reason of adjustment, e.g. discount

      Similiar to items, the URL encoding rule is `adjustments_<field name><number>`.
      For example, to give two discount adjustments, you can pass parameters
      like this

      - adjustments_amount1=-1000
      - adjustments_reason1=Coupon discount
      - adjustments_amount2=200
      - adjustments_reason2=Setup fee

Example:

::

    curl https://billing.balancedpayments.com/v1/invoices \
        -X POST \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "customer_guid=CUR1omRKGYYhqNaK1SyZqSbZ" \
        -d "amount=1000" \
        -d "appears_on_statement_as=FooBar Hosting" \
        -d "item_name1=Hosting Service A" \
        -d "item_amount1=1000" \
        -d "adjustments_amount1=-100" \
        -d "adjustments_reason1=Coupon discount"

Response:

::

    {
        "adjustments": [
            {
                "amount": -100,
                "reason": "Coupon discount"
            }
        ],
        "amount": 1000,
        "appears_on_statement_as": "FooBar Hosting",
        "created_at": "2013-08-16T00:00:00",
        "customer_guid": "CUR1omRKGYYhqNaK1SyZqSbZ",
        "effective_amount": 900,
        "external_id": null,
        "funding_instrument_uri": null,
        "guid": "IVS6Mo3mKLkUJKsJhtqkV7T7",
        "invoice_type": "customer",
        "items": [
            {
                "amount": 1000,
                "name": "Hosting Service A",
                "quantity": null,
                "type": null,
                "unit": null,
                "volume": null
            }
        ],
        "status": "init",
        "title": null,
        "total_adjustment_amount": -100,
        "transaction_type": "charge",
        "updated_at": "2013-08-16T00:00:00"
    }

Retrieve
~~~~~~~~

Retrieve an invoice  entity

Method
    GET
Endpoint
    /v1/invoices/<Invoice GUID>

Example:

::

    curl https://billing.balancedpayments.com/v1/invoices/IVS6Mo3mKLkUJKsJhtqkV7T7 \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "adjustments": [
            {
                "amount": -100,
                "reason": "Coupon discount"
            }
        ],
        "amount": 1000,
        "appears_on_statement_as": "FooBar Hosting",
        "created_at": "2013-08-16T00:00:00",
        "customer_guid": "CUR1omRKGYYhqNaK1SyZqSbZ",
        "effective_amount": 900,
        "external_id": null,
        "funding_instrument_uri": null,
        "guid": "IVS6Mo3mKLkUJKsJhtqkV7T7",
        "invoice_type": "customer",
        "items": [
            {
                "amount": 1000,
                "name": "Hosting Service A",
                "quantity": null,
                "type": null,
                "unit": null,
                "volume": null
            }
        ],
        "status": "init",
        "title": null,
        "total_adjustment_amount": -100,
        "transaction_type": "charge",
        "updated_at": "2013-08-16T00:00:00"
    }

Update
~~~~~~

An invoice can be created without a `funding_instrument_uri`. You can create
an invoice first, send it to customer, and let them decide how to pay the
bill. Once your customer decided to pay the bill, for example, with their 
credit card, you can then update the `funding_instrument_uri` of invoice
to the tokenlized credit card number. Billy will then try to settle the invoice 
with given funding istrument. This could also be useful when previous 
`funding_instrument_uri` is incorrect, or something goes wrong while 
processing, such as there is no sufficient fund in the credit card. In that case, 
invoice will become failed eventually, and you can ask your customer for 
another method to pay the bill, and update the `funding_instrument_uri` 
again with the new instrument URI.

Method
    PUT
Endpoint
    /v1/invoices/<Invoice GUID>
Parameters
    - **funding_instrument_uri** - The funding instrument URI to update

Example:

::

    curl https://billing.balancedpayments.com/v1/invoices/IVS6Mo3mKLkUJKsJhtqkV7T7 \
        -X PUT \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "funding_instrument_uri=/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno"

Response:

::

    {
        "adjustments": [
            {
                "amount": -100,
                "reason": "Coupon discount"
            }
        ],
        "amount": 1000,
        "appears_on_statement_as": "FooBar Hosting",
        "created_at": "2013-08-16T00:00:00",
        "customer_guid": "CUR1omRKGYYhqNaK1SyZqSbZ",
        "effective_amount": 900,
        "external_id": null,
        "funding_instrument_uri": "/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC1dEUPMmL1ljk4hWqeJxGno",
        "guid": "IVS6Mo3mKLkUJKsJhtqkV7T7",
        "invoice_type": "customer",
        "items": [
            {
                "amount": 1000,
                "name": "Hosting Service A",
                "quantity": null,
                "type": null,
                "unit": null,
                "volume": null
            }
        ],
        "status": "init",
        "title": null,
        "total_adjustment_amount": -100,
        "transaction_type": "charge",
        "updated_at": "2013-08-16T00:00:00"
    }

Refund
~~~~~~

Issue an refund to customer. Only settled invoices can be refunded.

Method
    POST
Endpoint
    /v1/invoices/<Invoice GUID>/refund
Parameters
    - **amount** - The amount to refund customer

Example:

::

    curl https://billing.balancedpayments.com/v1/invoices/IVS6Mo3mKLkUJKsJhtqkV7T7/refund \
        -X POST \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "amount=1000"

Response:

::

    {
        "adjustments": [
            {
                "amount": -100,
                "reason": "Coupon discount"
            }
        ],
        "amount": 1000,
        "appears_on_statement_as": "FooBar Hosting",
        "created_at": "2013-08-16T00:00:00",
        "customer_guid": "CUR1omRKGYYhqNaK1SyZqSbZ",
        "effective_amount": 900,
        "external_id": null,
        "funding_instrument_uri": null,
        "guid": "IVS6Mo3mKLkUJKsJhtqkV7T7",
        "invoice_type": "customer",
        "items": [
            {
                "amount": 1000,
                "name": "Hosting Service A",
                "quantity": null,
                "type": null,
                "unit": null,
                "volume": null
            }
        ],
        "status": "init",
        "title": null,
        "total_adjustment_amount": -100,
        "transaction_type": "charge",
        "updated_at": "2013-08-16T00:00:00"
    }

List
~~~~

List all invoices

Method
    GET
Endpoint
    /v1/invoices
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20

Example:

::

    curl https://billing.balancedpayments.com/v1/invoices \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "items": [
            {
                "adjustments": [
                    {
                        "amount": -100,
                        "reason": "Coupon discount"
                    }
                ],
                "amount": 1000,
                "appears_on_statement_as": "FooBar Hosting",
                "created_at": "2013-08-16T00:00:00",
                "customer_guid": "CUR1omRKGYYhqNaK1SyZqSbZ",
                "effective_amount": 900,
                "external_id": null,
                "funding_instrument_uri": null,
                "guid": "IVS6Mo3mKLkUJKsJhtqkV7T7",
                "invoice_type": "customer",
                "items": [
                    {
                        "amount": 1000,
                        "name": "Hosting Service A",
                        "quantity": null,
                        "type": null,
                        "unit": null,
                        "volume": null
                    }
                ],
                "status": "init",
                "title": null,
                "total_adjustment_amount": -100,
                "transaction_type": "charge",
                "updated_at": "2013-08-16T00:00:00"
            }
        ], 
        "limit": 20, 
        "offset": 0
    }

List transactions
~~~~~~~~~~~~~~~~~

List all transactions generated from the invoice

Method
    GET
Endpoint
    /v1/invoices/<Invoice GUID/transactions
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20


Transaction
-----------

Transactions are entities generated from an invoice. It represents transactions
we submit to underlying payment processor. You should notice that Billy 
currently only submits transactions to processor and doesn't care what happened
afterward. A transaction contains the current status, type of transaction, 
amount, funding instrument URI and failures. The state transition of a 
transaction is shown in following diagram. 

.. image:: _static/transaction_state_diagram.png
   :width: 100%

For all status:

 - **INIT** - just created transaction
 - **RETRYING** - attempt to submit but failed, retrying
 - **CANCELED** - the invoice is canceled before the transaction is done 
   or failed
 - **FAILED** - the transaction failure count exceeded limitation
 - **DONE** - the transaction is submitted successfully

Retrieve
~~~~~~~~

Retrieve a transaction entity

Method
    GET
Endpoint
    /v1/transactions/<Transaction GUID>

Example:

::

    curl https://billing.balancedpayments.com/v1/transactions/TXWRvbzADhsBHFhgkVMWB3Lb \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "guid": "TXWRvbzADhsBHFhgkVMWB3Lb", 
        "subscription_guid": "SUWRtr1b8s5tejhEPejybvwR", 
        "status": "done", 
        "transaction_type": "charge", 
        "amount": 500, 
        "appears_on_statement_as": null,
        "funding_instrument_uri": "/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC5ildoSnySGnXRfrYvH49eo", 
        "external_id": "/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/debits/WD5P9jvc7fLSoA6gYXxHkPd4", 
        "failure_count": 0, 
        "error_message": null, 
        "scheduled_at": "2013-10-03T05:09:07.702489",
        "created_at": "2013-10-03T05:09:07.709617", 
        "updated_at": "2013-10-03T05:09:10.837832"
    }

List
~~~~

List all transactions

Method
    GET
Endpoint
    /v1/transactions
Parameters
    - **offset** - Offset for pagination, default value is 0
    - **limit** - Limit for pagination, default value is 20

Example:

::

    curl https://billing.balancedpayments.com/v1/transactions \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb:

Response:

::

    {
        "items": [
            {
                "guid": "TXWRvbzADhsBHFhgkVMWB3Lb", 
                "subscription_guid": "SUWRtr1b8s5tejhEPejybvwR", 
                "status": "done", 
                "transaction_type": "charge", 
                "amount": 500, 
                "appears_on_statement_as": null,
                "funding_instrument_uri": "/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/cards/CC5ildoSnySGnXRfrYvH49eo", 
                "external_id": "/v1/marketplaces/TEST-MP7hkE8rvpbtYu2dlO1jU2wg/debits/WD5P9jvc7fLSoA6gYXxHkPd4", 
                "failure_count": 0, 
                "error_message": null, 
                "scheduled_at": "2013-10-03T05:09:07.702489",
                "created_at": "2013-10-03T05:09:07.709617", 
                "updated_at": "2013-10-03T05:09:10.837832"
            }
        ], 
        "limit": 20, 
        "offset": 0
    }
