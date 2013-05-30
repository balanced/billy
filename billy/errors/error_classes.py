
class NotFoundError(Exception):
    """
    Raised when object requested is not found.
    """
    pass

class BadIntervalError(Exception):
    """
    Raised when interval is not of relativedelta type
    """
    pass


class AlreadyExistsError(Exception):
    """
    Raised when the insertion already exists and can't be done.
    """
    pass

class InactiveObjectError(Exception):
    """
    Raised when an object (like plan or coupon) is being applied
    that is inactive
    """
    pass