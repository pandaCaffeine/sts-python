from sts.healthcheck.reader import HealthCheckReader
from sts.healthcheck.writer import HealthCheckWriter
from sts.models.bucket import BucketsInfo


class HealthCheckService(HealthCheckReader, HealthCheckWriter):
    _buckets_info: BucketsInfo | None = None

    def set_buckets_info(self, buckets_info: BucketsInfo):
        assert buckets_info, "buckets_info is required"
        assert self._buckets_info is None, "buckets_info is readonly"

        self._buckets_info = buckets_info

    @property
    def bucket_info(self) -> BucketsInfo:
        assert self._buckets_info, "set_buckets_info() was not called"
        return self._buckets_info


instance = HealthCheckService()
