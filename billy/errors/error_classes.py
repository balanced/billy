class BillyServiceError(Exception):

    """
    All billy errors extend from here.
    """
    pass


class NotFoundError(BillyServiceError):

    """
    Raised when object requested is not found.
    """
    pass


class BadIntervalError(BillyServiceError):

    """
    Raised when interval is not of relativedelta type
    """
    pass


class AlreadyExistsError(BillyServiceError):

    """
    Raised when the insertion already exists and can't be done.
    """
    pass


class ValidationError(BillyServiceError):

    """
    Raised if the parameter passed could not be validated.
    """
    pass


class LimitReachedError(BillyServiceError):

    """
    Raised when a predefined limit is reached, e.g. coupon max_redeem
    """
    pass
