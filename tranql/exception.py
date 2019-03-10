class TranQLException(Exception):
    def __init__(self, message):
        super().__init__(message)

class UndefinedVariableError(TranQLException):
    def __init__(self, message):
        super().__init__(message)
        
class UnableToGenerateQuestionError(TranQLException):
    def __init__(self, message):
        super().__init__(message)
        
class ServiceInvocationError(TranQLException):
    def __init__(self, message):
        super().__init__(message)

class MalformedResponseError(TranQLException):
    def __init__(self, message):
        super().__init__(message)
        
class IllegalConceptIdentifierError(TranQLException):
    def __init__(self, message):
        super().__init__(message)
