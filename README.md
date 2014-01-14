# Billy

Billy - The Open Source Recurring Billing System, powered by Balanced

[![Build Status](https://travis-ci.org/balanced/billy.png)](https://travis-ci.org/balanced/billy)

(In beta stage, use it on your own risk :D)

## Documents

Please visit

http://balancedbilly.readthedocs.org/en/latest/index.html

## Running It

To run billy (development mode), you need to install the package first.
As we don't want to mess the global Python environment, you should
create a virtual environmnet first and switch to it

```
virtualenv --no-site-packages env
source env/bin/activate
```

If above works correctly, you should see

```
(env) $
```

in you command line tool. The `(env)` indicates that you are currently
in the virtual Python environment. Then you need to install the billy project.
Here you run

```
python setup.py develop
```

This should install all required dependencies. Then you need to create 
tables in database, here you type

```
initialize_billy_db development.ini
```

This should create all necessary tables for you in a default SQLite database.

Then, to run the API web server, here you type

```
pserve development.ini --reload
```

To process recurring transactions, here you can type

```
process_billy_tx development.ini
```

You can setup a crontab job to run the process_billy_tx periodically.

## Running Unit and Functional Tests

To run tests, after installing billy project and all dependencies, you need
to install dependencies for testing, here you type:

```
pip install -r test-requirements.txt
```

And to run the tests, here you type

```
python setup.py nosetests
```

or, if you prefer run specific tests, you can run

```
nosetests billy/tests/functional
```

## Running Integration Tests

To run integration tests, here you type

```
nosetests billy/tests/integration
```

The default testing target URL is `http://127.0.0.1:6543`, to modify it, you can 
set environment variable `BILLY_TEST_URL`. To change balanced API key, you can set
`BILLY_TEST_PROCESSOR_KEY` variable. For example

```
export BILLY_TEST_URL=http://example-billy-api.com
export BILLY_TEST_PROCESSOR_KEY=MY_SECRET_KEY_HERE
nosetests billy/tests/integration
```
