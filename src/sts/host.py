from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from sts.api.hc import hc_router
from sts.api.images import images_router
from sts.bucket_management.service import BucketService
from sts.config import AppSettings
from sts.container import container
from sts.healthcheck.writer import HealthCheckWriter
from sts.logs import configure_logger


def _prepare_application() -> None:
    app_settings = container.get(AppSettings)
    configure_logger(app_settings)

    bucket_service = container.get(BucketService)
    bucket_info = bucket_service.create_buckets()

    hc_service = container.get(HealthCheckWriter)
    hc_service.set_buckets_info(bucket_info)


@asynccontextmanager
async def _app_lifespan(_: FastAPI):
    _prepare_application()
    yield
    container.close()

app = FastAPI(lifespan=_app_lifespan)
app.include_router(images_router)
app.include_router(hc_router)
setup_dishka(container, app)
