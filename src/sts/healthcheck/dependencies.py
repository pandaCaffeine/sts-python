from functools import lru_cache

from sts.healthcheck.service import HealthCheckService


@lru_cache
def get_health_check_service():
    return HealthCheckService()
