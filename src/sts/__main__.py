import sys

import uvicorn
from loguru import logger

from sts.config import app_settings
from sts.healthcheck.dependencies import get_health_check_service
from sts.images.buckets_service import BucketsService
from sts.images.dependencies import get_minio_client, get_storage_client
from sts.images.routes import images_router
from sts.healthcheck.routes import hc_route
from fastapi import FastAPI
from sts import __version__


def __configure_logger():
    logger.remove()
    logger.add(sys.stdout, level=app_settings.log_level, format=app_settings.log_fmt)
    logger.add(sys.stderr, level="ERROR", format=app_settings.log_fmt)
    logger.add("logs/log_{time}.log", level=app_settings.log_level, retention="10 days",
               format=app_settings.log_fmt)


def __create_fastapi_app() -> FastAPI:
    result = FastAPI()
    result.include_router(images_router)
    result.include_router(hc_route)
    return result


def __start_app():
    __configure_logger()

    l = logger.bind(source="core")
    minio = get_minio_client()
    storage_client = get_storage_client(minio)

    buckets_service = BucketsService(app_settings, storage_client, l)
    buckets_info = buckets_service.create_buckets()

    hc_service = get_health_check_service()
    hc_service.set_buckets_info(buckets_info)

    web_app = __create_fastapi_app()
    l.info("Starting web host")
    uvicorn.run(web_app, host="0.0.0.0", port=80, proxy_headers=True)


if __name__ == "__main__":
    print(f"sts v{__version__}")
    __start_app()
