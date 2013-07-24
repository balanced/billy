# Billy

Billy - The Open Source Recurring Billing System, powered by Balanced

(In active development. Consider it pre-alpha)

## Running It

There are three major parts to billy: the models, the api, and the web layer.
This library currently has the API and the models.

1. Create a pgsql DB called 'billy' with 'test' user and no password
2. Install requirements ```pip install -r requirements.txt```
3. Create the tables: ```python manage.py create_tables```
4. To run the api server run: ```python manage.py runserver```
5. Cron job this hourly: ```python manage.py billy_tasks```

Congrats. You've got recurring billing.

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
