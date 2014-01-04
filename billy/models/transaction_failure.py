from __future__ import unicode_literals

from billy.models import tables
from billy.models.base import BaseTableModel
from billy.models.base import decorate_offset_limit
from billy.utils.generic import make_guid


class TransactionFailureModel(BaseTableModel):

    TABLE = tables.TransactionFailure

    @decorate_offset_limit
    def list_by_context(self, context):
        """List transaction failures by a given context

        """
        Transaction = tables.Transaction
        TransactionFailure = tables.TransactionFailure

        if isinstance(context, Transaction):
            query = (
                self.session
                .query(TransactionFailure)
                .filter(TransactionFailure.transaction == context)
            )
        else:
            raise ValueError('Unsupported context {}'.format(context))

        query = query.order_by(TransactionFailure.created_at.desc())
        return query

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
