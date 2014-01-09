from __future__ import unicode_literals


class BillyError(RuntimeError):
    """Billy system error base class

    """
    def __init__(self, msg):
        super(BillyError, self).__init__(msg)
        self.msg = msg
