from functools import lru_cache
from typing import Annotated

from fastapi.params import Depends

from sts.healthcheck.service import HealthCheckService


@lru_cache
def _get_health_check_service():
    return HealthCheckService()

HealthCheckServiceDep = Annotated[HealthCheckService, Depends(_get_health_check_service)]
