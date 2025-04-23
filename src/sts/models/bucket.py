from pydantic.dataclasses import dataclass

from sts.models.enums import BucketStatus


@dataclass(frozen=True, slots=True)
class BucketsInfo:
    """ Buckets information """

    thumbnail_buckets: dict[str, BucketStatus] = dict()
    """ Map of thumbnail buckets to bucket status (created, exists, error) """
    source_buckets: dict[str, BucketStatus] = dict()
    """ Map of source buckets to bucket status (created, exists, error) """
    error: bool = True
    """ Returns true if it was not possible to validate or create any of source or thumbnail buckets """