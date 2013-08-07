# Billy

Billy - The Open Source Recurring Billing System, powered by Balanced

(In active development. Consider it pre-alpha)

## Running It

There are three major parts to billy: the models, the api, and the web layer.
This library currently has the API and the models.

1. Create a pgsql DB called 'billy' with 'test' user and no password
2. Install requirements ```pip install -r requirements.txt```
3. Create the tables: ```python manage.py create_tables```
4. To run the api server run: ```python manage.py run_api```
5. Cron job this hourly: ```python manage.py billy_tasks```

Congrats. You've got recurring billing.

## Models

The models should have all the methods necessary to bill recuringly. Generally,
modifactions to the underlying data should be done via the model methods not,
directly. This is to ensure that all the accounting is handled correctly.

To see how they work check out the interface tests
(tests/models/test_interface.py)

## Api

Check out the spec at api/spec.json, which is generated using api/spec.py


#### Major Todos:
- Redo import strucutre
- Redo commit/flush/rollback handling.
- Better transient exception handling.