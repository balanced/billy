#IN ACTIVE DEVELOPMENT! DO NOT USE!!!!
# Billy

Billy - The Open Source Recurring Billing System, powered by Balanced

## Proposal for Billy

Since Balanced is a dual-sided payments platform, `Billy` must support:

  - credit card charges
  - bank payments
  - bank deposits

These operations should be scheduled at an arbitrary frequency. Some
customers might want a recurring payout schedule for 7 days and a
recurring charge plan that's monthly.

`Billy` must be flexible enough to support scheduling changes, where
appropriate business logic is executed.

This essentially boils down to a scheduling problem, that will
have a large number of business rules on transition.

Given a `timer`, we subscribe to this timer with a `scheduler`, and that
`scheduler` contains a `task`.

All `tasks` are wrapped with a `scheduler`, which control the `tasks`
scheduling and exposes information such as when the time of next run
is scheduled, as well as if a `task` is retryable. A `scheduler` may schedule
other `tasks`.

All `tasks` are audited and generate events, which are called
`AuditEvents`. These `AuditEvents` are essentially line-items for an
`AuditFeed`. `AuditFeeds` are generated for a scheduler, or its
`frequency` execution, and are more commonly known as `invoices`. `Invoices`
are essentially the sum of all `AuditEvents`, or operations, that have
happened for a particular `task` during its scheduled period of
execution.

Here are some common tasks:

- `DebitTask` - Invokes a method that does some calculation dynamically to charge an account for a computed price.

- `FixedDebitTask` - What's commonly known as a plan, is a `DebitTask` with a FIXED price.

- `PayoutTask` - Invokes a method that does some calculation dynamically to issue a bank payout to an account for a computed amount.

- `FixedPayoutTask` - What's commonly known as payroll, is a `PayoutTask` with a FIXED price.

## Glossary

`frequency`:

  frequency = `PERIOD_OF_TIME` * `f(x)`

  `f(x)` can be considered an identity function, which we will call the
  `INTERVAL`.

  Through substitution:

  frequency = `PERIOD_OF_TIME` * `INTERVAL`

### Plans

```python
import billy

# create the goat plan to bill every 3 months.

billy.Plan.create(
    amount=100,
    description='the goat - silver',
    trial_period=None,
    frequency=billy.Frequency.MONTHLY,
    interval=3
)
```

#### Plan Frequency

```python
Frequency(object):
   YEARLY = 'yearly'
   MONTHLY = 'monthly'
   WEEKLY = 'weekly'
```

### Subscriptions


### Events
