import sys
from functools import lru_cache
from typing import Annotated

from fastapi.params import Depends
from loguru import logger, Logger

from app.config import AppSettings, app_settings


@lru_cache
def get_app_settings() -> AppSettings:
    return app_settings


@lru_cache
def get_logger(global_settings: Annotated[AppSettings, Depends(get_app_settings)]) -> Logger:
    logger.remove()
    logger.add(sys.stdout, level=global_settings.log_level, format=global_settings.log_fmt)
    logger.add(sys.stderr, level="ERROR", format=global_settings.log_fmt)
    logger.add("logs/log_{time}.log", level=app_settings.log_level, retention="10 days", format=app_settings.log_fmt)

    return logger


def get_request_logger(bucket: str | None, file_name: str | None, l: Annotated[Logger, Depends()]) -> Logger:
    return l.bind(bucket=bucket, file_name=file_name)
