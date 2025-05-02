import fastapi
import loguru
from dishka import make_container, Provider, Scope, AnyOf
from dishka.integrations.fastapi import FastapiProvider
from minio import Minio

from sts.buckets.minio import MinioBucketService
from sts.buckets.service import BucketService
from sts.config import AppSettings, BucketsMap, create_buckets_map, S3Settings
from sts.file_storage.client import FileStorageClient
from sts.file_storage.minio_client import MinioFileStorageClient
from sts.file_storage.minio_scanner import MinioFileStorageScanner
from sts.file_storage.scanner import FileStorageScanner
from sts.healthcheck.reader import HealthCheckReader
from sts.healthcheck.service import HealthCheckService
from sts.healthcheck.writer import HealthCheckWriter
from sts.images.service import ThumbnailService
from sts.logs import ILogger


def _provide_app_config() -> AppSettings:
    return AppSettings()


def _provide_buckets_map(app_settings: AppSettings) -> BucketsMap:
    return create_buckets_map(app_settings)


def _provide_s3_settings(app_settings: AppSettings) -> S3Settings:
    return app_settings.s3


def _provide_minio_client(s3_settings: S3Settings) -> Minio:
    return Minio(endpoint=s3_settings.endpoint, access_key=s3_settings.access_key,
                 secret_key=s3_settings.secret_key, region=s3_settings.region,
                 cert_check=s3_settings.trust_cert, secure=s3_settings.use_tsl)


def _provide_storage_client(minio: Minio) -> FileStorageClient:
    return MinioFileStorageClient(minio)


def _provide_request_logger(req: fastapi.Request) -> ILogger:
    return loguru.logger.bind(path=req.base_url.path)


def _provide_file_storage_scanner(storage_client: FileStorageClient, buckets_map: BucketsMap) -> FileStorageScanner:
    return MinioFileStorageScanner(storage_client, buckets_map)


def _provide_thumbnail_service(storage_client: FileStorageClient, file_storage_scanner: FileStorageScanner,
                               req_logger: ILogger) -> ThumbnailService:
    return ThumbnailService(storage_client, file_storage_scanner, req_logger)


def _provide_hc_service() -> AnyOf[HealthCheckReader, HealthCheckWriter]:
    return HealthCheckService()

def _provide_bucket_service(app_settings: AppSettings, storage_client: FileStorageClient) -> BucketService:
    l = loguru.logger.bind(source='bucket_service')
    return MinioBucketService(app_settings=app_settings, storage_client=storage_client, l=l)


_provider = Provider()
# application scope
_provider.provide(_provide_app_config, scope=Scope.APP)
_provider.provide(_provide_buckets_map, scope=Scope.APP)
_provider.provide(_provide_s3_settings, scope=Scope.APP)
_provider.provide(_provide_storage_client, scope=Scope.APP)
_provider.provide(_provide_hc_service, scope=Scope.APP)
_provider.provide(_provide_minio_client, scope=Scope.APP)
_provider.provide(_provide_bucket_service, scope=Scope.APP)
# request scope
_provider.provide(_provide_request_logger, scope=Scope.REQUEST)
_provider.provide(_provide_file_storage_scanner, scope=Scope.REQUEST)
_provider.provide(_provide_thumbnail_service, scope=Scope.REQUEST)

container = make_container(_provider, FastapiProvider())
