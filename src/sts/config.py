import typing
from functools import lru_cache

from pydantic import BaseModel, HttpUrl, model_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource, JsonConfigSettingsSource

from sts.models.enums import ImageFormat


class ImageSize(BaseModel):
    """Represents the dimensions of an image with width and height.

        Attributes:
            w: The width of the image in pixels. Defaults to 200.
            h: The height of the image in pixels. Defaults to 200.
        """

    w: int = 200
    h: int = 200

    @classmethod
    def parse(cls, source: str) -> typing.Self:
        """Parse a string representation of image size.

                Args:
                    source: A string in format "WxH" (e.g., "1920x1080").

                Returns:
                    An ImageSize instance with parsed dimensions.

                Raises:
                    ValueError: If the source string cannot be parsed into valid dimensions.
                """
        try:
            parts = [int(p) for p in source.split('x') if p]
            if len(parts) == 2:
                return cls(w=parts[0], h=parts[1])
        except ValueError:
            pass
        raise ValueError(f"Couldn't parse '{source}' into ImageSize")


class S3HttpRetries(BaseModel):
    total: int = 3
    backoff_factor: float = 0.1
    status_forcelist: list[int] = [500, 502, 503, 504]


class S3HttpSettings(BaseModel):
    maxsize: int = 10
    block: bool = False
    retries: S3HttpRetries = S3HttpRetries()


class S3Settings(BaseModel):
    """Configuration settings for S3-compatible object storage.

    Attributes:
        endpoint: The S3 endpoint address. Defaults to "localhost:9000".
        access_key: The S3 access key. Defaults to "MINIO_AK".
        secret_key: The S3 secret key. Defaults to "MINIO_SK".
        region: The S3 region. Defaults to "eu-west-1".
        use_tsl: Whether to use TLS/SSL. Defaults to False.
        trust_cert: Whether to trust certificates. Defaults to True.
        http: Http settings for client
    """
    endpoint: str = "localhost:9000"
    access_key: str = "MINIO_AK"
    secret_key: str = "MINIO_SK"
    region: str = "eu-west-1"
    use_tsl: bool = False
    trust_cert: bool = True
    http: S3HttpSettings = S3HttpSettings()

    @classmethod
    def parse(cls, value: str) -> tuple[typing.Self, str | None]:
        """Parse an S3 connection URL into settings and optional source bucket.

        Args:
            value: A URL string in format "scheme://user:pass@host:port/region/bucket".

        Returns:
            A tuple containing S3Settings instance and optional source bucket name.

        Raises:
            ValueError: If the URL is invalid or missing required components.
        """

        s3_url = HttpUrl(value)
        if not s3_url.path:
            raise ValueError(f"Value '{value}' is not a valid S3 connection string")

        fragments = [f for f in s3_url.path.split('/') if f]
        if not fragments:
            raise ValueError(f"Url path '{s3_url.path}' doesn't contain region")

        region = fragments[0]
        source_bucket = fragments[1] if len(fragments) > 1 else None

        return cls(
            endpoint=f"{s3_url.host}:{s3_url.port}",
            access_key=s3_url.username or "",
            secret_key=s3_url.password or "",
            region=region,
            trust_cert=s3_url.scheme == "https",
            use_tsl=s3_url.scheme == "https",
        ), source_bucket


class BucketSettings(BaseModel):
    """Configuration settings for a storage bucket.

    Attributes:
        size: The image size settings for this bucket. Defaults to ImageSize().
        life_time_days: Number of days before objects expire. Defaults to 30.
        source_bucket: The name of the source bucket.
        alias: An optional alias for bucket reference.
        format: The image format for this bucket. Defaults to ImageFormat.NONE.
        format_args: Additional format-specific arguments as a dictionary.
    """
    size: ImageSize = ImageSize()
    life_time_days: int = 30
    source_bucket: str
    alias: str | None = None
    format: ImageFormat = ImageFormat.NONE
    format_args: dict[str, typing.Any] | None = None

    @classmethod
    def parse(cls, s: str | None) -> dict | None:
        """Parse a query string into bucket settings dictionary.

        Args:
            s: A query string (e.g., "key1=val1&key2=val2").

        Returns:
            A dictionary of parsed key-value pairs, or None if input is empty.
        """
        if not s:
            return None
        from urllib import parse
        return {k: v[0] for k, v in parse.parse_qs(s).items()}


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables and config files.

    Attributes:
        s3: S3 storage configuration. Defaults to S3Settings().
        buckets: A dictionary of bucket name to BucketSettings mappings.
        source_bucket: The default source bucket name.
        log_level: Logging level. Defaults to 'info'.
        log_fmt: Logging format string.
        size: Default image size. Defaults to ImageSize().
        uvicorn: Dictionary of uvicorn server settings.
    """

    s3: S3Settings = S3Settings()
    buckets: dict[str, BucketSettings] = Field(default_factory=dict)
    source_bucket: str | None = None
    log_level: str = 'info'
    log_fmt: str = "[{process}] {time} | {level}: {extra} {message}"
    size: ImageSize = ImageSize()
    uvicorn: dict[str, typing.Any] = Field(default_factory=dict)

    model_config = SettingsConfigDict(
        env_file=".env",
        nested_model_default_partial_update=True,
        env_nested_delimiter="__",
        extra='ignore',
        case_sensitive=False,
        json_file="config.json",
        enable_decoding=False,
    )

    @model_validator(mode='before')
    @classmethod
    def before_validator(cls, data: typing.Any):
        """Validate and prepare settings data before model construction.

        Args:
            data: Raw input data from configuration sources.

        Returns:
            Prepared dictionary ready for model construction.
        """
        if not isinstance(data, dict):
            return data

        raw_dict = dict(data)
        cls._prepare_uvicorn(raw_dict)
        cls._prepare_s3(raw_dict)
        cls._prepare_size(raw_dict)
        cls._prepare_buckets(raw_dict)
        return raw_dict

    @classmethod
    def _prepare_uvicorn(cls, raw_dict: dict) -> None:
        uvicorn_settings = raw_dict.setdefault('uvicorn', {})
        uvicorn_settings.setdefault('host', '0.0.0.0')
        uvicorn_settings.setdefault('port', 80)
        uvicorn_settings.setdefault('proxy_headers', True)

    @classmethod
    def _prepare_s3(cls, raw_dict: dict) -> None:
        if isinstance(raw_dict.get('s3'), str):
            s3_settings, source_bucket = S3Settings.parse(raw_dict['s3'])
            raw_dict['s3'] = s3_settings
            raw_dict.setdefault('source_bucket', source_bucket)

    @classmethod
    def _prepare_size(cls, raw_dict: dict) -> None:
        if isinstance(raw_dict.get('size'), str):
            raw_dict['size'] = ImageSize.parse(raw_dict['size'])

    @classmethod
    def _prepare_buckets(cls, raw_dict: dict) -> None:
        buckets = raw_dict.get('buckets')
        if not isinstance(buckets, dict):
            return

        source_bucket = str(raw_dict.get('source_bucket') or '')
        default_size = raw_dict.get('size')

        for key, b in buckets.items():
            if isinstance(b, str):
                b = BucketSettings.parse(b) or {}
            if not isinstance(b, dict):
                continue

            b.setdefault('source_bucket', source_bucket)
            if not b.get('source_bucket'):
                raise ValueError(f"For bucket '{key}' source_bucket was not set")

            b['size'] = ImageSize.parse(b['size']) if isinstance(b.get('size'), str) else (
                    b.get('size') or default_size)
            if not b['size']:
                raise ValueError(f"For bucket '{key}' size was not set")

            buckets[key] = b

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
    source_buckets = [s.source_bucket for s in settings.buckets.values() if s.source_bucket]
    alias_map = {b.alias: name for name, b in settings.buckets.items() if b.alias}

    base_source = settings.source_bucket or source_buckets[0]
    buckets_dict = {**settings.buckets, base_source: BucketSettings(source_bucket=base_source, size=settings.size)}

    if not settings.source_bucket:
        source_buckets.append(base_source)

    return BucketsMap(
        source_bucket=base_source,
        buckets=buckets_dict,
        all_source_buckets=set(source_buckets),
        alias_map=alias_map,
    )


@lru_cache
def get_app_settings() -> AppSettings:
    """Get the cached application settings instance.

    Returns:
        The singleton AppSettings instance.
    """
    return AppSettings()


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
