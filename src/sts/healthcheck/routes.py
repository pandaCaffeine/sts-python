from fastapi import APIRouter
from starlette import status
from starlette.responses import Response

from sts import __version__
from sts.healthcheck.service import instance as hc_instance


hc_route = APIRouter()


@hc_route.get("/hc")
@hc_route.get("/health")
def get_health_check(response: Response) -> dict:
    result = hc_instance.bucket_info
    if result.error:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return {'status': hc_instance.bucket_info, 'version': __version__}
