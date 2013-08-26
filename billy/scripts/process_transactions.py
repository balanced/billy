from __future__ import unicode_literals
import os
import sys
import logging

import transaction as db_transaction
from pyramid.paster import (
    get_appsettings,
    setup_logging,
)
from pyramid.path import DottedNameResolver

from billy.models import setup_database
from billy.models.subscription import SubscriptionModel
from billy.models.transaction import TransactionModel


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

    resolver = DottedNameResolver()
    if processor is None:
        processor_factory = settings['billy.processor_factory']
        processor_factory = resolver.maybe_resolve(processor_factory)
        processor = processor_factory()

    # yield all transactions and commit before we process them, so that
    # we won't double process them. 
    with db_transaction.manager:
        logger.info('Yielding transaction ...')
        subscription_model.yield_transactions()

    with db_transaction.manager:
        logger.info('Processing transaction ...')
        tx_model.process_transactions(processor)
    logger.info('Done')
