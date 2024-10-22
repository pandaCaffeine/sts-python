from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends
from starlette.responses import Response
from starlette import status

from app.healthcheck.dependencies import get_health_check_service
from app.healthcheck.service import HealthCheckService
from app.models import BucketsInfo

hc_route = APIRouter()


@hc_route.get("/hc")
@hc_route.get("/health")
def get_health_check(service: Annotated[HealthCheckService, Depends(get_health_check_service)],
                     response: Response) -> BucketsInfo:
    result = service.bucket_info
    if result.error:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return service.bucket_info
