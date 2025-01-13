from dataclasses import dataclass, field
from typing import Tuple

import pydantic
import pydantic.networks
from pydantic import BaseModel, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource, JsonConfigSettingsSource


@dataclass(frozen=True, slots=True)
class ImageSize:
    w: int = 200
    """ Image width, default value is 200px """

    h: int = 200
    """ Image height, default value is 200px """


class _BucketSettings(BaseModel):
    size: ImageSize | str | None = None
    """ Thumbnail's size in the bucket, 200x200px by default """

    life_time_days: int = 30
    """ How many days files in the bucket live, in days. 30 days by default. Set to zero, to make life time infinity """

    source_bucket: str | None = None
    """ Overrides default source bucket, can be None """

    alias: str | None = None
    """ Optional alias for the bucket, can be used for alternative routes """


@dataclass(frozen=True, slots=True)
class BucketSettings:
    size: ImageSize
    """ Thumbnail's size in the bucket, 200x200px by default """

    source_bucket: str
    """ Overrides default source bucket, can be None """

    life_time_days: int = 30
    """ How many days files in the bucket live, in days. 30 days by default. Set to zero, to make life time infinity """

    alias: str | None = None
    """ Optional alias for the bucket, can be used for alternative routes """


@dataclass(frozen=True, slots=True)
class S3Settings:
    endpoint: str = "localhost:9000"
    """ Host """
    access_key: str = "MINIO_AK"
    """ Access key """
    secret_key: str = "MINIO_SK"
    """ Secret key """
    region: str = "eu-west-1"
    """ Storage region, eu-west-1 by default """
    use_tsl: bool = False
    """ Flag to use secure connection, False by default """
    trust_cert: bool = True
    """ Set True to trust secure certificate and do not validate it, True by default """


class _AppBaseSettings(BaseSettings):
    """ Application settings """

    s3: S3Settings | HttpUrl = S3Settings()
    """ S3 or minio connection parameters """

    buckets: dict[str, _BucketSettings] | None = None
    """ Collection of buckets with thumbnail settings """

    source_bucket: str | None = None
    """ Bucket with source images to process """

    log_level: str = "INFO"
    """ Logging level """

    log_fmt: str = "{time} | {level}: {extra} {message}"
    """ Logging message format """

    size: ImageSize = ImageSize(200, 200)
    """ Thumbnail's default image size, 200x200px be default """

    model_config = SettingsConfigDict(env_file=".env", nested_model_default_partial_update=True,
                                      env_nested_delimiter="__", extra='ignore', case_sensitive=False,
                                      json_file="config.json")

    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, env_settings, JsonConfigSettingsSource(
            settings_cls), dotenv_settings, file_secret_settings


@dataclass(frozen=True, slots=True)
class AppSettings:
    s3: S3Settings = S3Settings()
    """ S3 or minio connection parameters """

    buckets: dict[str, BucketSettings] = field(default_factory=lambda: {})
    """ Collection of buckets with thumbnail settings """

    source_bucket: str = "images"
    """ Bucket with source images to process """

    log_level: str = "INFO"
    """ Logging level """

    log_fmt: str = "{time} | {level}: {extra} {message}"
    """ Logging message format """

    size: ImageSize = ImageSize()
    """ Thumbnail's default image size, 200x200px be default """


@dataclass(frozen=True, slots=True)
class BucketsMap:
    source_bucket: str
    buckets: dict[str, BucketSettings]
    all_source_buckets: set[str]
    alias_map: dict[str, str]


def _parse_size(source: str) -> ImageSize:
    """ Converts string {w}x{h} into ImageSize object """
    assert source and len(source) > 0, "source is required"
    try:
        str_parts = [int(p) for p in source.split('x') if p]
        if len(str_parts) == 2:
            return ImageSize(w=str_parts[0], h=str_parts[1])
    except ValueError:
        pass

    raise ValueError(f"Couldn't parse source string '{source}' into ImageSize")


def _parse_size_or_default(source: ImageSize | str | None, default_size: ImageSize) -> ImageSize:
    if not source:
        return default_size

    if isinstance(source, str):
        return _parse_size(source)

    return source


def _parse_path(path: str) -> Tuple[str, str | None]:
    fragments = [str(t) for t in path.split('/') if t]
    if len(fragments) < 1:
        raise ValueError("Invalid path string")

    if len(fragments) > 1:
        return fragments[0], fragments[1]

    return fragments[0], None


def _url_to_s3settings(s3_url: pydantic.networks.HttpUrl) -> Tuple[S3Settings, str | None]:
    assert s3_url, "s3_url is required"
    assert s3_url.path, "s3_url is not set"
    region, source_bucket = _parse_path(s3_url.path)

    return S3Settings(endpoint=f"{s3_url.host}:{s3_url.port}", access_key=s3_url.username or "",
                      secret_key=s3_url.password or "", region=region, trust_cert=s3_url.scheme == 'https',
                      use_tsl=s3_url.scheme == 'https'), source_bucket


def _base_app_settings_to_app_settings(base_settings: _AppBaseSettings) -> AppSettings:
    source_bucket = base_settings.source_bucket
    s3: S3Settings
    url_source_bucket: str | None = None
    if isinstance(base_settings.s3, pydantic.networks.HttpUrl):
        s3, url_source_bucket = _url_to_s3settings(base_settings.s3)
    else:
        s3 = base_settings.s3
    source_bucket = url_source_bucket or source_bucket
    if not source_bucket:
        raise ValueError("Source bucket was not configured, check configuration")

    default_size = base_settings.size
    if isinstance(default_size, str):
        default_size = _parse_size(default_size)

    if not base_settings.buckets:
        raise ValueError("Buckets were not configure, check configuration")

    parsed_buckets = dict[str, BucketSettings]()
    for k, v in base_settings.buckets.items():
        bucket_settings = BucketSettings(size=_parse_size_or_default(v.size, default_size),
                                         source_bucket=v.source_bucket or source_bucket,
                                         life_time_days=v.life_time_days, alias=v.alias)
        parsed_buckets[k] = bucket_settings

    return AppSettings(s3=s3, buckets=parsed_buckets, source_bucket=source_bucket,
                       log_level=base_settings.log_level, log_fmt=base_settings.log_fmt, size=default_size)


def _get_buckets_map(settings: AppSettings) -> BucketsMap:
    source_buckets = [s.source_bucket for s in settings.buckets.values() if s.source_bucket is not None]
    source_buckets.append(settings.source_bucket)

    alias_map = dict[str, str]()
    buckets_dict: dict[str, BucketSettings] = dict[str, BucketSettings]()
    for bucket_name, bucket_cfg in settings.buckets.items():
        buckets_dict[bucket_name] = bucket_cfg
        if bucket_cfg.alias:
            alias_map[bucket_cfg.alias] = bucket_name

    # source bucket cfg to map
    source_bucket_cfg = BucketSettings(source_bucket=settings.source_bucket, size=settings.size)
    buckets_dict[settings.source_bucket] = source_bucket_cfg

    return BucketsMap(alias_map=alias_map, buckets=buckets_dict, source_bucket=settings.source_bucket,
                      all_source_buckets=set(source_buckets))


if __name__ == 'main':
    app_settings: AppSettings = _base_app_settings_to_app_settings(_AppBaseSettings())
    bucket_map: BucketsMap = _get_buckets_map(app_settings)
