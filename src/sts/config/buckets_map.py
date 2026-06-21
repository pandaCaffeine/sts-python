from functools import lru_cache

from pydantic import BaseModel

from sts.config.loader import get_app_settings
from sts.config.models import BucketSettings, AppSettings


class BucketsMap(BaseModel):
    """A mapping of buckets with metadata for bucket resolution.

    Attributes:
        source_bucket: The primary source bucket name.
        buckets: Dictionary of bucket name to BucketSettings mappings.
        all_source_buckets: Set of all source bucket names.
        alias_map: Dictionary mapping aliases to bucket names.
    """
    source_bucket: str
    buckets: dict[str, BucketSettings]
    all_source_buckets: set[str]
    alias_map: dict[str, str]


def _build_buckets_map(settings: AppSettings) -> BucketsMap:
    declared_sources = [s.source_bucket for s in settings.buckets.values() if s.source_bucket]
    alias_map = {b.alias: name for name, b in settings.buckets.items() if b.alias}

    if not (base_source := settings.source_bucket or (declared_sources[0] if declared_sources else None)):
        raise ValueError(
            "Cannot resolve source bucket: set 'source_bucket' in AppSettings "
            "or specify 'source_bucket' for al least one bucket."
        )
    buckets_dict = {**settings.buckets, base_source: BucketSettings(source_bucket=base_source, size=settings.size)}

    if not settings.source_bucket:
        declared_sources.append(base_source)

    return BucketsMap(
        source_bucket=base_source,
        buckets=buckets_dict,
        all_source_buckets=set(declared_sources),
        alias_map=alias_map,
    )


def create_buckets_map(settings: AppSettings | None = None) -> BucketsMap:
    """Create a buckets map from settings or use cached settings.

    Args:
        settings: Optional AppSettings instance. If None, retrieves cached settings.

    Returns:
        A BucketsMap for bucket resolution.
    """
    settings = settings or get_app_settings()
    return _build_buckets_map(settings)


@lru_cache
def get_buckets_map() -> BucketsMap:
    return create_buckets_map()
