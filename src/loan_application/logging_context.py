import logging
from contextvars import ContextVar

user_id_ctx: ContextVar[str] = ContextVar("user_id", default="-")


class UserContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.user_id = user_id_ctx.get()
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(UserContextFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s user=%(user_id)s %(name)s: %(message)s"
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)