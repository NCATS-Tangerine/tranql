class TranQLException(Exception):
    def __init__(self, message, details=""):
        super().__init__(message)
        self.details = details

class UndefinedVariableError(TranQLException):
    def __init__(self, message):
        super().__init__(message)

class InvalidTransitionException(TranQLException):
    def __init__(self, source, target, edge, explanation):
        super().__init__(f"Invalid transition between {str(source)} and {str(target)}{' with predicate ' + str(edge.predicate) if edge != None and edge.predicate != None else ''}")
        self.details = explanation
        
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
