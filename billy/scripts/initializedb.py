from __future__ import unicode_literals
import os
import sys

from pyramid.paster import (
    get_appsettings,
    setup_logging,
)

from billy.models import setup_database
from billy.models.tables import DeclarativeBase


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [alembic_uri]\n'
          '(example: "%s development.ini alembic.ini")' % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2 or len(argv) > 3:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    settings = setup_database({}, **settings)
    engine = settings['engine']

    DeclarativeBase.metadata.create_all(engine)

    if len(argv) != 3:
        return
    alembic_uri = argv[2]
    # load the Alembic configuration and generate the
    # version table, "stamping" it with the most recent rev:
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config(alembic_uri)
    command.stamp(alembic_cfg, 'head')
