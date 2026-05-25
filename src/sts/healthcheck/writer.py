from abc import ABC, abstractmethod

from sts.models.bucket import BucketsInfo


class HealthCheckWriter(ABC):
    """ Service to write health check information """

    @abstractmethod
    def set_buckets_info(self, buckets_info: BucketsInfo) -> None:
         """Stores buckets information for health check validation. """
         ...
