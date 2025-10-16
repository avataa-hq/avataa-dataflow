class CustomException(Exception):
    pass


class InternalError(CustomException):
    pass


class ResourceNotFoundError(CustomException):
    pass


class ValidationError(CustomException):
    pass


class SourceConnectionError(CustomException):
    pass


class ConflictError(CustomException):
    pass
