from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class BucketSettings(BaseModel):
    width: int = 200
    """
    Thumbnail's width in the bucket, 200px by default 
    """
    height: int = 200
    """
    Thumbnail's height in the bucket, 200px by default
    """
    life_time_days: int = 30
    """
    How many days files in the bucket live, in days. 30 days by default. Set to zero, to make life time infinity.
    """
    source_bucket: str | None = None
    """
    Overrides default source bucket, can be None
    """
    alias: str | None = None
    """
    Optional alias for the bucket, can be used for alternative routes
    """


class S3Settings(BaseModel):
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


class AppSettings(BaseSettings):
    s3: S3Settings = S3Settings()
    """ S3 or minio connection parameters """
    buckets: dict[str, BucketSettings] = dict()
    """ Collection of buckets with thumbnail settings """
    source_bucket: str = "images"
    """ Bucket with source images to process """
    model_config = SettingsConfigDict(env_file=".env", nested_model_default_partial_update=True,
                                      env_nested_delimiter="__", extra='ignore', case_sensitive=False)
    log_level: str = "INFO"
    """
    Logging level
    """
    log_fmt: str = "{time} | {level}: {extra} {message}"
    """
    Logging message format
    """


app_settings: AppSettings = AppSettings()