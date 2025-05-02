import sys
from typing import Protocol, Any

from loguru import logger

from sts.config import AppSettings


class ILogger(Protocol):
    """ Logger protocol to wrap up loguru class """

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    def info(self, message: str, *args: Any, **kwargs: Any) -> None: ...

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None: pass


def configure_logger(app_settings: AppSettings) -> None:
    """
    Setups logging configuration for the app. This method removes all default settings and adds new handlers:
    to console and to file. Log files are saved to logs/log_{time}.log files with retentiotion for 10 days.
    :param app_settings: Application settings
    :return: None
    """

    logger.remove()
    logger.add(sys.stdout, level=app_settings.log_level.upper(), format=app_settings.log_fmt)
    logger.add(sys.stderr, level="ERROR", format=app_settings.log_fmt)
    logger.add("logs/log_{time}.log", level=app_settings.log_level.upper(), retention="10 days",
               format=app_settings.log_fmt)
