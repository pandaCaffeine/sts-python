from abc import ABC, abstractmethod

from sts.models.bucket import BucketsInfo


class BucketService(ABC):
    """ Service to perform buckets operations """

    @abstractmethod
    def create_buckets(self) -> BucketsInfo:
        """ Tries to create source and thumbnail buckets in storage. If a bucket already exists - it won't be created."""
        pass
