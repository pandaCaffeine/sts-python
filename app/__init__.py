__author__ = "Nikita Sakhno"
__license__ = "MIT License"
__version__ = "1.1.0"

from fastapi import FastAPI

from app.healthcheck.routes import hc_route
from app.images.routes import images_router

web_app = FastAPI()
web_app.include_router(images_router)
web_app.include_router(hc_route)
