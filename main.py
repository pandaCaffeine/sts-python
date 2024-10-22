import sys

import uvicorn
from loguru import logger

from app.dependencies import get_app_settings
from app.healthcheck.dependencies import get_health_check_service
from app.images.buckets_service import BucketsService
from app.images.dependencies import get_minio_client, get_storage_client
from app.main import web_app


def __configure_logger():
    app_settings = get_app_settings()
    logger.remove()
    logger.add(sys.stdout, level=app_settings.log_level, format=app_settings.log_fmt)
    logger.add(sys.stderr, level="ERROR", format=app_settings.log_fmt)
    logger.add("logs/log_{time}.log", level=app_settings.log_level, retention="10 days",
               format=app_settings.log_fmt)


def __start_app():
    __configure_logger()

    app_settings = get_app_settings()
    l = logger.bind(source="core")
    minio = get_minio_client()
    storage_client = get_storage_client(minio)

    buckets_service = BucketsService(app_settings, storage_client, l)
    buckets_info = buckets_service.create_buckets()

    hc_service = get_health_check_service()
    hc_service.set_buckets_info(buckets_info)

    l.info("Starting web host")
    uvicorn.run(web_app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    __start_app()
