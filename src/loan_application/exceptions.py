class NotFoundError(Exception):
    def __init__(self, message: str):
        self.message = message          


class InvalidInputError(Exception):
    def __init__(self, message: str = "Invalid input"):
        self.message = message
