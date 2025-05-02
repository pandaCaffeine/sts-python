from abc import ABC, abstractmethod

from sts.models.bucket import BucketsInfo


class HealthCheckReader(ABC):
    """ Service to read health check information """

    @property
    @abstractmethod
    def bucket_info(self) -> BucketsInfo:
        """ Returns buckets info set before """
        pass