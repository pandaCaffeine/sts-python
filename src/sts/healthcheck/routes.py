from fastapi import APIRouter
from starlette import status
from starlette.responses import Response

from sts import __version__
from sts.healthcheck.dependencies import HealthCheckServiceDep

hc_route = APIRouter()


@hc_route.get("/hc")
@hc_route.get("/health")
def get_health_check(service: HealthCheckServiceDep,
                     response: Response) -> dict:
    result = service.bucket_info
    if result.error:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return {'status': service.bucket_info, 'version': __version__}
