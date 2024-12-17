from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends
from starlette import status
from starlette.responses import Response

from sts.healthcheck.dependencies import get_health_check_service
from sts.healthcheck.service import HealthCheckService
from sts import __version__

hc_route = APIRouter()


@hc_route.get("/hc")
@hc_route.get("/health")
def get_health_check(service: Annotated[HealthCheckService, Depends(get_health_check_service)],
                     response: Response) -> dict:
    result = service.bucket_info
    if result.error:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return {'status': service.bucket_info, 'version': __version__}
