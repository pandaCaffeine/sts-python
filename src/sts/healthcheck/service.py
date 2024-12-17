from sts.models import BucketsInfo


class HealthCheckService:
    __buckets_info: BucketsInfo = None

    def set_buckets_info(self, buckets_info: BucketsInfo):
        assert buckets_info is not None, "buckets_info is required"
        assert self.__buckets_info is None, "buckets_info is readonly"

        self.__buckets_info = buckets_info

    @property
    def bucket_info(self) -> BucketsInfo:
        return self.__buckets_info