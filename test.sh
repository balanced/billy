#!/bin/bash
if [ -z "$BILLY_TEST_INTEGRATION" ]; then
    python setup.py nosetests --verbosity=2 --with-coverage
else
    initialize_billy_db test.ini
    pserve test.ini --daemon
    nosetests billy/tests/integration --verbosity=2 --with-coverage
fi
