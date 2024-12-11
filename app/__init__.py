__author__ = "Nikita Sakhno"
__license__ = "MIT License"
__version__ = "1.1.0"

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import bucket_map
from app.healthcheck.routes import hc_route
from app.images.routes import images_router
from app.stats.middleware import stats_middleware

web_app = FastAPI()
web_app.include_router(images_router)
web_app.include_router(hc_route)

# noinspection PyTypeChecker
web_app.add_middleware(BaseHTTPMiddleware, dispatch=stats_middleware)
