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
from billy.models.model_factory import ModelFactory
from billy.api.utils import get_processor_factory


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
    try:
        if processor is None:
            processor_factory = get_processor_factory(settings)
        else:
            processor_factory = lambda: processor
        factory = ModelFactory(
            session=session,
            processor_factory=processor_factory,
            settings=settings,
        )
        subscription_model = factory.create_subscription_model()
        tx_model = factory.create_transaction_model()

        # yield all transactions and commit before we process them, so that
        # we won't double process them.
        with db_transaction.manager:
            logger.info('Yielding transaction ...')
            subscription_model.yield_invoices()

        with db_transaction.manager:
            logger.info('Processing transaction ...')
            tx_model.process_transactions()
        logger.info('Done')
    finally:
        session.close()
