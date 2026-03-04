class Error(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message


class InvalidEnum(ValueError):
    pass


class InvalidParameter(Error):
    def __init__(self, param, allowed_params=None):
        message = f"Parameter {param} is not allowed."
        if allowed_params:
            message = f"Parameter {param} is not allowed.  Accepted parameters include: [{','.join(allowed_params)}]"
        super().__init__(message)
        self.param = param
        self.allowed_params = allowed_params


class RequiredParameterNotFound(Error):
    def __init__(self, param):
        message = f"Required parameter {param} was not provided."
        super().__init__(message)
        self.param = param


class ItemAlreadyExists(Error):
    def __init__(self, message=None):
        if not message:
            message = "An item already exists with the given key"

        super().__init__(message)


class InvalidKegtronAdvertisementData(Error):
    def __init__(self, message=None):
        if not message:
            message = "Invalid Kegtron Advertisement Data Packet"

        super().__init__(message)