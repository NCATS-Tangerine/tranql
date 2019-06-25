class TranQLException(Exception):
    def __init__(self, message, details=""):
        super().__init__(message)
        self.details = details

class UndefinedVariableError(TranQLException):
    def __init__(self, message):
        super().__init__(message)

class UnableToGenerateQuestionError(TranQLException):
    def __init__(self, message):
        super().__init__(message)

class ServiceInvocationError(TranQLException):
    def __init__(self, message, details=""):
        super().__init__(message, details)

class RequestTimeoutError(TranQLException):
    def __init__(self, message, details=""):
        super().__init__(message, details)

class MalformedResponseError(TranQLException):
    def __init__(self, message):
        super().__init__(message)

class IllegalConceptIdentifierError(TranQLException):
    def __init__(self, message):
        super().__init__(message)

class UnknownServiceError(TranQLException):
    def __init__(self, message):
        super().__init__(message)
