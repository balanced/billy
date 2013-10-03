REST API reference
==================

The official endpoint of Billy API is

::

    https://billing.balancedpayments.com

By the time I am writing this, it is not deployed yet. And once it is deployed,
it will be in **beta** stage for a while. Be ready to encounter some bugs if you 
are going to use it. When you find a bug, or you have any suggestion to this
project, please create an issue in our `GitHub repo`_.


.. _`GitHub repo`: https://github.com/balanced/billy

All HTTP response except errors will be in JSON format. Other format is not 
supported. To access the API, you need an API key, except the one for registering
a company. The API key should be passed as the username for HTTP basic 
authentication, leave the password blank.


Company
-------

A company is an account for the Billy system, you need to pass your Balanced
API key, so that Billy can process payments with Balanced for you. It has a 
generated API key which is required for any further calls to other methods. 

.. note::

    You **MUST** keep these API keys as **secret**, do not share them with 
    anyone, do not post them on IRC. Also, currently, Billy API key cannot be 
    retrived or reset easily, if you lost it, you can only contact 
    administrator to ask them reset it for you.

Create
~~~~~~

Create a company and return the record. Only this method does not require an
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
        -d "processor_key=ef13dce2093b11e388de026ba7d31e6f"

Response:

::

    {
        "guid": "CPMM8C8Uhkt4pDeJ8oqJu8Nj", 
        "api_key": "6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb", 
        "created_at": "2013-10-02T05:29:43.953987", 
        "updated_at": "2013-10-02T05:29:43.953987"
    }

Retrive
~~~~~~~

Retrive a company record

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

A plan is a setup for recurring payment processing, it has the amount to 
charge or payout and the frequency of transaction.

Create
~~~~~~

Create a plan and return the record.

Method
    POST
Endpoint
    /v1/plans
Parameters
    - **plan_type** - The type of this plan, can be either **charge** for 
      charging customer or **payout** for paying out.
    - **frequency** - The frequency to schedule charging or paying out to 
      customer. Can be either

        - daily
        - weekly
        - monthly
        - yearly

      When it is **monthly** and the schedule started at end of a month, the 
      closest day to the started one in a month will be selected for following 
      transactions. For example, the started date time is 2013-01-30, then 
      following transactions will occur at 2013-02-28, 2013-03-30 and so on.
    - **amount** - The amount in USD dollar to charge or payout to customer
    - **interval** - (optional) The interval of frequency period to multiply, 
      the default value is 1. For example, to charge or payout a customer
      by two weeks frequency, you can set the frequency to **weekly**, and set
      the **interval** to 2, then the schedule will be in a biweekly manner.


Example:

::

    curl https://billing.balancedpayments.com/v1/plans \
        -u 6w9KwCPCmCQJpEYgCCtjaPmbLNQSavv5sX4mCZ9Sf6pb: \
        -d "plan_type=charge" \
        -d "amount=5" \
        -d "frequency=monthly"

Response:

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

Retrive
~~~~~~~

Retrive a plan record

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
        "amount": "5.00", 
        "frequency": "monthly", 
        "deleted": false, 
        "created_at": "2013-10-02T05:48:26.210843", 
        "updated_at": "2013-10-02T05:48:26.210843"
    }

Delete
~~~~~~

Delete a plan and return record.

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
        "amount": "5.00", 
        "frequency": "monthly", 
        "deleted": true, 
        "created_at": "2013-10-02T05:48:26.210843", 
        "updated_at": "2013-10-02T05:48:26.210843"
    }

Customer
--------

TODO:

Subscription
------------

TODO:

Transaction
-----------

TODO: