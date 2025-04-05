import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from loguru import logger

from sts import __version__
from sts.config import get_app_settings
from sts.healthcheck.routes import hc_route
from sts.healthcheck.service import instance as hc_instance
from sts.images.buckets_service import BucketsService
from sts.images.dependencies import get_storage_client
from sts.images.routes import images_router


def __configure_logger():
    app_settings = get_app_settings()
    logger.remove()
    logger.add(sys.stdout, level=app_settings.log_level.upper(), format=app_settings.log_fmt)
    logger.add(sys.stderr, level="ERROR", format=app_settings.log_fmt)
    logger.add("logs/log_{time}.log", level=app_settings.log_level.upper(), retention="10 days",
               format=app_settings.log_fmt)


async def __startup():
    app_settings = get_app_settings()
    storage_client = get_storage_client()
    buckets_service = BucketsService(app_settings, storage_client, logger.bind(source="core"))
    buckets_info = await buckets_service.create_buckets()

    hc_service = hc_instance
    hc_service.set_buckets_info(buckets_info)


@asynccontextmanager
async def __lifespan(_: FastAPI):
    await __startup()
    yield


def __create_fastapi_app() -> FastAPI:
    result = FastAPI(lifespan=__lifespan)
    result.include_router(images_router)
    result.include_router(hc_route)
    return result


if __name__ == "__main__":
    __configure_logger()

    print(f"sts v{__version__}")
    app_cfg = get_app_settings()
    print(f" * s3 host: {app_cfg.s3.endpoint}\n"
          f" * source bucket: {app_cfg.source_bucket or '<undefined>'}\n"
          f" * buckets:")

    for bucket, bucket_cfg in app_cfg.buckets.items():
        print(f" ** {bucket_cfg.source_bucket or '<undefined>'} -> {bucket} @ {bucket_cfg.alias}")

    l = logger.bind(source="core")
    l.info("Starting web host")

    web_app = __create_fastapi_app()
    uvicorn.run(web_app, **app_cfg.uvicorn)
