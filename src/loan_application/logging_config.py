import logging
import sys
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)


# ANSI colours: green 2xx, cyan 3xx, yellow 4xx, red 5xx.
STATUS_COLOURS = {2: "\x1b[32m", 3: "\x1b[36m", 4: "\x1b[33m", 5: "\x1b[31m"}


def coloured_status(status_code: int) -> str:
    colour = STATUS_COLOURS.get(status_code // 100)
    if colour is None or not sys.stderr.isatty():
        return str(status_code)
    return f"{colour}{status_code}\x1b[0m"


class LogContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        record.user_id = user_id_var.get() or "-"
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(request_id)s"
            " | user_id=%(user_id)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(LogContextFilter())

    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logging.getLogger("uvicorn").handlers = []
    logging.getLogger("uvicorn").propagate = True
    logging.getLogger("uvicorn.access").disabled = True
