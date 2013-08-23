import os
import sys

import balanced
import transaction as db_transaction
from pyramid.paster import (
    get_appsettings,
    setup_logging,
)

from billy.models import setup_database
from billy.models.transaction import TransactionModel
from billy.models.processors.balanced_payments import BalancedProcessor


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    settings = setup_database({}, **settings)

    balanced.configure(settings['balanced.api_key'])
    session = settings['session']
    tx_model = TransactionModel(session)
    processor = BalancedProcessor()

    with db_transaction.manager:
        tx_model.process_transactions(processor)
    print('done')
