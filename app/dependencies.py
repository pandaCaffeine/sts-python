from functools import lru_cache

from app.config import AppSettings, BucketsMap, app_settings


@lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()


@lru_cache
def get_buckets_map() -> BucketsMap:
    source_buckets = [s.source_bucket for s in app_settings.buckets.values() if s.source_bucket is not None]
    source_buckets.append(app_settings.source_bucket)

    alias_map = dict[str, str]()
    for bucket_name, bucket_cfg in app_settings.buckets.items():
        if bucket_cfg.alias is None:
            continue
        bucket_cfg.source_bucket = bucket_cfg.source_bucket or app_settings.source_bucket
        alias_map[bucket_cfg.alias] = bucket_name

    return BucketsMap(alias_map=alias_map, buckets=app_settings.buckets, source_bucket=app_settings.source_bucket,
                      all_source_buckets=set(source_buckets))
