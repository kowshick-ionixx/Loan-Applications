from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, error: str, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    # Turns any AppError into a JSON response like {"error": "NOT_FOUND", "message": "..."}
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "message": exc.message},
    )
