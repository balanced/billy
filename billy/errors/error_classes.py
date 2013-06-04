class BillySerivceError(Exception):
    """
    All billy errors extend from here.
    """
    pass


class NotFoundError(BillySerivceError):
    """
    Raised when object requested is not found.
    """
    pass

class BadIntervalError(BillySerivceError):
    """
    Raised when interval is not of relativedelta type
    """
    pass


class AlreadyExistsError(BillySerivceError):
    """
    Raised when the insertion already exists and can't be done.
    """
    pass


class ValidationError(BillySerivceError):
    """
    Raised if the parameter passed could not be validated.
    """
    pass


class LimitReachedError(Exception):
    """
    Raised when a predefined limit is reached, e.g. coupon max_redeem
    """
    pass

