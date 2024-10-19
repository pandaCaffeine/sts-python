from fastapi import FastAPI

from app.images.routes import images_router

web_app = FastAPI()
web_app.include_router(images_router)
