class NotFoundError(Exception):
    def __init__(self, message: str = "Resource not found"):
        self.message = message
        super().__init__(message)


class CustomerNotFound(NotFoundError):
    def __init__(self, customer_id: int | None = None, message: str | None = None):
        if message is None:
            if customer_id is None:
                message = "Customer not found"
            else:
                message = f"Customer with id {customer_id} not found"
        super().__init__(message)


class InvalidInputError(Exception):
    def __init__(self, message: str = "Invalid input"):
        self.message = message
        super().__init__(message)


class ConflictError(Exception):
    def __init__(self, message: str = "Conflict with existing data"):
        self.message = message
        super().__init__(message)
