class SaltBoostrapBaseException(Exception):
    """
    Base class for salt bootstrap exceptions
    """


class SaltBootstrapExit(SystemExit):
    """
    """


class RequiredBinaryNotFound(SaltBoostrapBaseException):
    """
    Exception raised when a required binary is not found
    """
