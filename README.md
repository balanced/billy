# Billy

Billy - The Open Source Recurring Billing System, powered by Balanced


## Proposal for Billy

### Plans

```python
import billy

# create the goat plan to bill every 3 months.

billy.Plan.create(
    amount=100,
    description='the goat - silver',
    trial_period=None,
    frequency=billing.Frequency.MONTHLY,
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
