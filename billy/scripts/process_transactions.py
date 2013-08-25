from __future__ import unicode_literals
import os
import sys
import logging

import transaction as db_transaction
from pyramid.paster import (
    get_appsettings,
    setup_logging,
)

from billy.models import setup_database
from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel
from billy.models.processors.balanced_payments import BalancedProcessor


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv, processor=None):
    logger = logging.getLogger(__name__)

    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    settings = setup_database({}, **settings)

    session = settings['session']
    subscription_model = SubscriptionModel(session)
    tx_model = TransactionModel(session)
    if processor is None:
        processor = BalancedProcessor()

    with db_transaction.manager:
        logger.info('Yielding transaction ...')
        subscription_model.yield_transactions()
        logger.info('Processing transaction ...')
        tx_model.process_transactions(processor)
    logger.info('Done')
