from sts.models import BucketsInfo


class HealthCheckService:
    _buckets_info: BucketsInfo | None = None

    def set_buckets_info(self, buckets_info: BucketsInfo):
        assert buckets_info is not None, "buckets_info is required"
        assert self._buckets_info is None, "buckets_info is readonly"

        self._buckets_info = buckets_info

    @property
    def bucket_info(self) -> BucketsInfo:
        assert self._buckets_info, "set_buckets_info() was not called"
        return self._buckets_info