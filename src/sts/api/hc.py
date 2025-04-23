import fastapi
import starlette.status
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaSyncRoute
from fastapi.routing import APIRouter

from sts.healthcheck.reader import HealthCheckReader
from sts.models.bucket import BucketsInfo

hc_router = APIRouter(route_class=DishkaSyncRoute)

@hc_router.get('/hc')
@hc_router.get('/health')
def get_hc(response: fastapi.Response, service: FromDishka[HealthCheckReader]) -> BucketsInfo:
    result = service.bucket_info
    if result.error:
        response.status_code = starlette.status.HTTP_500_INTERNAL_SERVER_ERROR
    return result
