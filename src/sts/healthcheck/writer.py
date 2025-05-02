from abc import ABC, abstractmethod

from sts.models.bucket import BucketsInfo


class HealthCheckWriter(ABC):
    """ Service to write healthcheck information """

    @abstractmethod
    def set_buckets_info(self, buckets_info: BucketsInfo):
        """ Sets buckets info """
        pass
