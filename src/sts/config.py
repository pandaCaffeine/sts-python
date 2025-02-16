import typing
from urllib import parse

from pydantic import BaseModel, HttpUrl, model_validator, Field
from pydantic.dataclasses import dataclass
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource, JsonConfigSettingsSource


@dataclass(frozen=True, slots=True)
class ImageSize:
    w: int = 200
    """ Image width, default value is 200px """

    h: int = 200
    """ Image height, default value is 200px """


class BucketSettings(BaseModel):
    size: ImageSize = ImageSize(200, 200)
    """ Thumbnail's size in the bucket, 200x200px by default """

    life_time_days: int = 30
    """ How many days files in the bucket live, in days. 30 days by default. Set to zero, to make life time infinity """

    source_bucket: str
    """ Overrides default source bucket, can be None """

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


def _parse_bucket_settings(s: str | None) -> dict | None:
    if not s:
        return None

    raw_values = parse.parse_qs(s)
    raw_dict = {k: v[0] for k, v in raw_values.items()}
    return raw_dict


def _parse_path(path: str) -> tuple[str, str | None]:
    fragments = [str(t) for t in path.split('/') if t]
    if len(fragments) < 1:
        raise ValueError(f"Url path '{path}' doesn't contain region")

    if len(fragments) > 1:
        return fragments[0], fragments[1]

    return fragments[0], None


def _parse_s3_settings(value: str) -> tuple[S3Settings, str | None]:
    s3_url = HttpUrl(value)
    if not s3_url.path or not len(s3_url.path):
        raise ValueError(f"Value '{value}' was not recognized as a valid S3 connection string")

    region, source_bucket = _parse_path(s3_url.path)
    return S3Settings(endpoint=f"{s3_url.host}:{s3_url.port}", access_key=s3_url.username or "",
                      secret_key=s3_url.password or "", region=region, trust_cert=s3_url.scheme == 'https',
                      use_tsl=s3_url.scheme == 'https'), source_bucket


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


class AppSettings(BaseSettings):
    """ Application settings """

    s3: S3Settings = S3Settings()
    """ S3 or minio connection parameters """

    buckets: dict[str, BucketSettings] = Field(default_factory=dict)
    """ Collection of buckets with thumbnail settings """

    source_bucket: str | None = None
    """ Bucket with source images to process """

    log_level: str = 'info'
    """ Logging level. Options: critical, error, warning, info, debug, trace. Default: info """

    log_fmt: str = "{time} | {level}: {extra} {message}"
    """ Logging message format """

    size: ImageSize = ImageSize()
    """ Thumbnail's default image size, 200x200px be default """

    uvicorn: dict[str, typing.Any] = Field(default_factory=dict[str, typing.Any])
    """ uvicorn specific settings """

    model_config = SettingsConfigDict(env_file=".env", nested_model_default_partial_update=True,
                                      env_nested_delimiter="__", extra='ignore', case_sensitive=False,
                                      json_file="config.json", enable_decoding=False)

    # noinspection PyNestedDecorators
    @model_validator(mode='before')
    @classmethod
    def before_validator(cls, data: typing.Any) -> typing.Any:
        result = data
        if isinstance(data, dict):
            raw_dict = dict(data)

            uvicorn_settings = raw_dict.setdefault('uvicorn', dict[str, typing.Any]())
            uvicorn_settings.setdefault('host', '0.0.0.0')
            uvicorn_settings.setdefault('port', 80),
            uvicorn_settings.setdefault('proxy_headers', True)

            if isinstance(raw_dict.get('s3', None), str):
                s3_str = str(raw_dict['s3'])
                s3_settings, source_bucket = _parse_s3_settings(s3_str)
                raw_dict['s3'] = s3_settings
                raw_dict['source_bucket'] = raw_dict.get('source_bucket', source_bucket)

            source_bucket = str(raw_dict.get('source_bucket', None))
            default_size = raw_dict.get('size', None)
            if isinstance(default_size, str):
                default_size = _parse_size(str(default_size))
                raw_dict['size'] = default_size

            if isinstance(raw_dict.get('buckets', None), dict):
                buckets_dict = dict(raw_dict['buckets'])
                for key, b in buckets_dict.items():
                    if isinstance(b, str):
                        b = _parse_bucket_settings(str(b))

                    if not isinstance(b, dict):
                        continue

                    bucket_obj = dict(b)
                    bucket_obj['source_bucket'] = bucket_obj.get('source_bucket', source_bucket)
                    if not bucket_obj['source_bucket']:
                        raise ValueError(
                            f"For bucket '{key}' source_bucket was not set, check configuration or "
                            "set root 'source_bucket' as fallback value.")

                    bucket_size = bucket_obj.get('size', default_size)
                    if isinstance(bucket_size, str):
                        bucket_size = _parse_size(str(bucket_size))

                    bucket_obj['size'] = bucket_size
                    if not bucket_obj['size']:
                        raise ValueError(f"For bucket '{key}' size was not set, check configuration or "
                                         "set root 'size' as fallback value.")
                    buckets_dict[key] = bucket_obj

                raw_dict['buckets'] = buckets_dict
            result = raw_dict

        return result

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
class BucketsMap:
    source_bucket: str
    buckets: dict[str, BucketSettings]
    all_source_buckets: set[str]
    alias_map: dict[str, str]


def _get_buckets_map(settings: AppSettings) -> BucketsMap:
    source_buckets = [s.source_bucket for s in settings.buckets.values() if s.source_bucket is not None]

    alias_map = dict[str, str]()
    buckets_dict: dict[str, BucketSettings] = dict[str, BucketSettings]()
    for bucket_name, bucket_cfg in settings.buckets.items():
        buckets_dict[bucket_name] = bucket_cfg
        if bucket_cfg.alias:
            alias_map[bucket_cfg.alias] = bucket_name

    # source bucket cfg to map
    base_source_bucket = settings.source_bucket or source_buckets[0]
    source_bucket_cfg = BucketSettings(source_bucket=base_source_bucket, size=settings.size)
    buckets_dict[base_source_bucket] = source_bucket_cfg
    if not settings.source_bucket:
        source_buckets.append(base_source_bucket)

    return BucketsMap(alias_map=alias_map, buckets=buckets_dict, source_bucket=base_source_bucket,
                      all_source_buckets=set(source_buckets))


_app_settings: AppSettings | None = None
_buckets_map: BucketsMap | None = None


def get_app_settings() -> AppSettings:
    global _app_settings
    if not _app_settings:
        _app_settings = AppSettings()
    return _app_settings


def get_buckets_map() -> BucketsMap:
    global _buckets_map
    if not _buckets_map:
        _buckets_map = _get_buckets_map(get_app_settings())
    return _buckets_map
