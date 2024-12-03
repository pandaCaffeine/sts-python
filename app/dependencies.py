from functools import lru_cache
from typing import Annotated

from fastapi.params import Depends
from pydantic import HttpUrl

from app.config import AppSettings, BucketsMap, app_base_settings, BucketSettings, S3Settings


def _parse_path(path: str) -> (str, str | None):
    assert path, "path is required"
    fragments: list[str] = [t for t in path.split('/') if t]
    if len(fragments) > 1:
        return fragments[0], fragments[1]
    return fragments[0], None


@lru_cache
def get_app_settings() -> AppSettings:
    base_settings = app_base_settings
    s3: S3Settings
    source_bucket = app_base_settings.source_bucket
    if isinstance(base_settings.s3, HttpUrl):
        s3_url: HttpUrl = base_settings.s3
        region, bucket = _parse_path(s3_url.path)
        source_bucket = bucket | source_bucket
        s3 = S3Settings(
            endpoint=f"{s3_url.host}:{s3_url.port}", access_key=s3_url.username,
            secret_key=s3_url.password, region=region, trust_cert=s3_url.scheme == 'https',
            use_tsl=s3_url.scheme == 'https'
        )
    else:
        s3 = base_settings.s3

    assert source_bucket, "source_bucket is not configured"
    return AppSettings(
        s3=s3,
        source_bucket=source_bucket,
        buckets=base_settings.buckets,
        log_level=base_settings.log_level,
        log_fmt=base_settings.log_fmt
    )


@lru_cache
def get_buckets_map(app_settings: Annotated[AppSettings, Depends(get_app_settings)]) -> BucketsMap:
    source_buckets = [s.source_bucket for s in app_settings.buckets.values() if s.source_bucket is not None]
    source_buckets.append(app_settings.source_bucket)

    alias_map = dict[str, str]()
    buckets_dict: dict[str, BucketSettings] = dict[str, BucketSettings]()
    for bucket_name, bucket_cfg in app_settings.buckets.items():
        if bucket_cfg.alias is None:
            continue
        buckets_dict[bucket_name] = bucket_cfg.model_copy(
            update={'source_bucket': bucket_cfg.source_bucket or app_settings.source_bucket})
        alias_map[bucket_cfg.alias] = bucket_name

    # source bucket cfg to map
    source_bucket_cfg = BucketSettings()
    source_bucket_cfg.source_bucket = app_settings.source_bucket
    buckets_dict[app_settings.source_bucket] = source_bucket_cfg

    return BucketsMap(alias_map=alias_map, buckets=buckets_dict, source_bucket=app_settings.source_bucket,
                      all_source_buckets=set(source_buckets))
