from __future__ import unicode_literals

from billy.db import tables
from billy.models.base import BaseTableModel
from billy.utils.generic import make_guid


class TransactionFailureModel(BaseTableModel):

    TABLE = tables.TransactionFailure

    def create(
        self,
        transaction,
        error_message,
        error_code=None,
        error_number=None,
    ):
        """Create a failure for and return

        """
        failure = self.TABLE(
            guid='TF' + make_guid(),
            transaction=transaction,
            error_message=error_message,
            error_code=error_code,
            error_number=error_number,
        )
        self.session.add(failure)
        self.session.flush()
        return failure
