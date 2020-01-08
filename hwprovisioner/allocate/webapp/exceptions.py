"""
custom exceptions
"""


class AllocateValidationError(Exception):
    """
    raised when a validation error is encountered
    """
    def __init__(self, errors=None):
        self.errors = errors
        super().__init__()

    def __str__(self):
        return ", ".join(self.errors)


class AllocateServerError(AllocateValidationError):
    """
    user-facing error for server issues
    """
