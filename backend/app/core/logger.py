"""
Structured logging configuration using standard logging and structlog.
"""
import logging
import sys
try:
    import structlog
    _has_structlog = True
except ImportError:
    _has_structlog = False


def setup_logging() -> None:
    """Configures structured JSON logging for production and readable console logs for dev."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    if _has_structlog:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.TimeStamper(fmt="iso"),
                (
                    structlog.dev.ConsoleRenderer()
                    if settings.ENVIRONMENT == "development"
                    else structlog.processors.JSONRenderer()
                ),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )


class _FallbackLogger:
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _format(self, msg: str, kwargs: dict) -> str:
        if kwargs:
            extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
            return f"{msg} {extra}"
        return msg

    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(self._format(msg, kwargs), *args)

    def info(self, msg: str, *args, **kwargs):
        self._logger.info(self._format(msg, kwargs), *args)

    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(self._format(msg, kwargs), *args)

    def warn(self, msg: str, *args, **kwargs):
        self._logger.warning(self._format(msg, kwargs), *args)

    def error(self, msg: str, *args, **kwargs):
        self._logger.error(self._format(msg, kwargs), *args)

    def critical(self, msg: str, *args, **kwargs):
        self._logger.critical(self._format(msg, kwargs), *args)


if _has_structlog:
    logger = structlog.get_logger()
else:
    logger = _FallbackLogger(logging.getLogger("orca"))
