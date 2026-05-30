import uvicorn
from loguru import logger

from sts import __version__
from sts.bucket_management.service import BucketService
from sts.config import AppSettings
from sts.container import container
from sts.logs import configure_logger


def _start_app():
    l = logger.bind(source="core")
    app_settings = container.get(AppSettings)

    buckets_service = container.get(BucketService)
    buckets_service.create_buckets()

    l.info("Starting web host")
    uvicorn.run("sts.host:app", **app_settings.uvicorn)


if __name__ == "__main__":
    print(f"sts v{__version__}")
    settings = container.get(AppSettings)
    configure_logger(settings)
    print(f" * s3 host: {settings.s3.endpoint}\n"
          f" * source bucket: {settings.source_bucket or '<undefined>'}\n"
          f" * buckets:")

    for bucket, bucket_cfg in settings.buckets.items():
        print(f" ** {bucket_cfg.source_bucket or '<undefined>'} -> {bucket} @ {bucket_cfg.alias}")

    _start_app()
