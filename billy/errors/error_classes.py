
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


class ValidationError(Exception):
    """
    Raised if the parameter passed could not be validated.
    """
    pass

