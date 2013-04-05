# Billy

Billy - The Open Source Recurring Billing System, powered by Balanced

## Proposal for Billy

Since Balanced is a dual-sided payments platform, `Billy` must support:

  - credit card charges
  - bank deposits

These operations should be scheduled at an arbitrary frequency. Some
customers might want a recurring payout schedule for 7 days and a
recurring charge plan that's monthly.

`Billy` must be flexible enough to support scheduling changes, where
appropriate business logic is executed.

This essentially boils down to a scheduling problem, that will
have a large number of business rules on transition.

Given a scheduler, we configure it with a task that contains
scheduling details.

This task controls its scheduling and exposes information such as when
the time of next run is scheduled, as well as if it's retryable. Tasks
may schedule other tasks.


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
