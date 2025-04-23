import sys

import uvicorn
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from loguru import logger

from sts import __version__
from sts.api.hc import hc_router
from sts.api.images import images_router
from sts.config import AppSettings
from sts.container import container
from sts.buckets.service import BucketService
from sts.healthcheck.writer import HealthCheckWriter


def __configure_logger(app_settings: AppSettings):
    logger.remove()
    logger.add(sys.stdout, level=app_settings.log_level.upper(), format=app_settings.log_fmt)
    logger.add(sys.stderr, level="ERROR", format=app_settings.log_fmt)
    logger.add("logs/log_{time}.log", level=app_settings.log_level.upper(), retention="10 days",
               format=app_settings.log_fmt)


def __create_fastapi_app() -> FastAPI:
    app = FastAPI()
    app.include_router(images_router)
    app.include_router(hc_router)

    setup_dishka(container=container, app=app)
    return app


def __start_app():
    l = logger.bind(source="core")
    app_settings = container.get(AppSettings)

    buckets_service = container.get(BucketService)
    buckets_info = buckets_service.create_buckets()

    hc_service = container.get(HealthCheckWriter)
    hc_service.set_buckets_info(buckets_info)

    web_app = __create_fastapi_app()
    l.info("Starting web host")

    uvicorn.run(web_app, **app_settings.uvicorn)


if __name__ == "__main__":
    print(f"sts v{__version__}")
    settings = container.get(AppSettings)
    __configure_logger(settings)
    print(f" * s3 host: {settings.s3.endpoint}\n"
          f" * source bucket: {settings.source_bucket or '<undefined>'}\n"
          f" * buckets:")

    for bucket, bucket_cfg in settings.buckets.items():
        print(f" ** {bucket_cfg.source_bucket or '<undefined>'} -> {bucket} @ {bucket_cfg.alias}")

    __start_app()
