import math

from pydantic import BaseModel


class Page[T](BaseModel):
    """One page of a list, with the metadata a client needs to fetch the rest."""

    items: list[T]
    page: int
    size: int
    total: int
    pages: int

    @classmethod
    def of(cls, items: list, page: int, size: int, total: int) -> "Page[T]":
        """`pages` is 0 when there is nothing to list; a page past the end is
        returned empty rather than as a 404."""
        return cls(
            items=items,
            page=page,
            size=size,
            total=total,
            pages=math.ceil(total / size),
        )


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


PROTECTED_RESPONSES: dict[int | str, dict] = {
    400: {"model": ValidationErrorResponse, "description": "Invalid input"},
    401: error("Missing, invalid or expired token"),
    403: error("Not allowed for this user, or customer profile required"),
}
