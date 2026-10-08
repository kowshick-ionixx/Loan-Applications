import logging
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIdFilter(logging.Filter):
    # Adds the current request id to every log line
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(request_id)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(RequestIdFilter())

    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    logging.getLogger("uvicorn").handlers = []
    logging.getLogger("uvicorn").propagate = True
    logging.getLogger("uvicorn.access").disabled = True
