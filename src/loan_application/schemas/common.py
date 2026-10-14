from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: str | None


class FieldError(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    error: str
    details: list[FieldError]
    request_id: str | None


def error(description: str) -> dict:
    return {"model": ErrorResponse, "description": description}


# Shown in /docs for every protected route.
PROTECTED_RESPONSES: dict[int | str, dict] = {
    400: {"model": ValidationErrorResponse, "description": "Invalid input"},
    401: error("Missing, invalid or expired token"),
    403: error("Not allowed for this user, or customer profile required"),
}
