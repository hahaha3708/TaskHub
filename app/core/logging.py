import logging

from app.core.config import settings

LOGGER_NAME = "taskhub"


def configure_logging() -> None:
    level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    return logging.getLogger(name)
