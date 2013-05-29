
class NotFoundError(ValueError):
    """
    Raised when object requested is not found.
    """
    pass

class BadIntervalError(ValueError):
    """
    Raised when interval is not of relativedelta type
    """
    pass


class AlreadyExistsError(Exception):
    """
    Raised when the insertion already exists and can't be done.
    """
    pass