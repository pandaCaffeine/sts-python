"""
Dependency injection container configuration using Dishka.

This module sets up the dependency injection container for the application,
organizing providers into APP and REQUEST scopes for optimal resource management.
"""
from urllib.parse import urljoin

from jwt import PyJWKClient
from sts.config.auth import AuthSettings, AuthMode, OidcSettings
import fastapi
import loguru
import urllib3
from dishka import make_container, Provider, Scope, Container, AnyOf
from dishka.integrations.fastapi import FastapiProvider
from minio import Minio

from sts.bucket_management.minio import MinioBucketService
from sts.bucket_management.service import BucketService
from sts.config import AppSettings, BucketsMap, create_buckets_map, S3Settings
from sts.file_storage.client import FileStorageClient
from sts.file_storage.minio_client import MinioFileStorageClient
from sts.file_storage.minio_scanner import MinioFileStorageScanner
from sts.file_storage.scanner import FileStorageScanner
from sts.healthcheck.reader import HealthCheckReader
from sts.healthcheck.service import HealthCheckService
from sts.healthcheck.writer import HealthCheckWriter
from sts.images.lock_manager import LockManager
from sts.images.thumbnail import ThumbnailService
from sts.logs import ILogger
from sts.security.authenticator import Authenticator
from sts.security.extractor import TokenExtractor
from sts.security.jwt_verifier import JWTVerifier
from sts.security.off_jwt_verifier import OffJWTVerifier
from sts.security.oidc_jwt_verifier import OidcJWTVerifier


def _provide_app_settings() -> AppSettings:
    """Provide application settings from configuration."""
    return AppSettings()


def _provide_auth_settings(app_settings: AppSettings) -> AuthSettings:
    """Provide authentication settings from application settings."""
    return app_settings.auth


def _provide_token_extractor(auth: AuthSettings) -> TokenExtractor:
    cookie_name = "access_token" if auth.oidc is None else auth.oidc.cookie_name
    return TokenExtractor(cookie_name=cookie_name)


def _provide_authenticator(auth: AuthSettings, verifier: JWTVerifier,
                           token_extractor: TokenExtractor, logger: ILogger) -> Authenticator:
    return Authenticator(auth_mode=auth.mode, verifier=verifier, token_extractor=token_extractor,
                         logger=logger)


def _provide_buckets_map(app_settings: AppSettings) -> BucketsMap:
    """Provide buckets mapping based on application settings."""
    return create_buckets_map(app_settings)


def _provide_s3_settings(app_settings: AppSettings) -> S3Settings:
    """Provide S3/Minio configuration settings."""
    return app_settings.s3


def _provide_minio_client(s3_settings: S3Settings) -> Minio:
    """Create and configure Minio client."""
    http = urllib3.PoolManager(
        maxsize=s3_settings.http.maxsize,
        block=s3_settings.http.block,
        retries=urllib3.Retry(
            total=s3_settings.http.retries.total,
            backoff_factor=s3_settings.http.retries.backoff_factor,
            status_forcelist=s3_settings.http.retries.status_forcelist,
        )
    )

    return Minio(
        endpoint=s3_settings.endpoint,
        access_key=s3_settings.access_key,
        secret_key=s3_settings.secret_key,
        region=s3_settings.region,
        cert_check=s3_settings.trust_cert,
        secure=s3_settings.use_tsl,
        http_client=http,
    )


def _provide_storage_client(minio: Minio) -> FileStorageClient:
    """Provide file storage client backed by Minio."""
    return MinioFileStorageClient(minio)


def _provide_request_logger(req: fastapi.Request) -> ILogger:
    """Provide request-scoped logger with request path context."""
    return loguru.logger.bind(path=req.base_url.path)


def _provide_file_storage_scanner(
        storage_client: FileStorageClient,
        buckets_map: BucketsMap,
) -> FileStorageScanner:
    """Provide file storage scanner for directory traversal."""
    return MinioFileStorageScanner(storage_client, buckets_map)


def _provide_thumbnail_service(
        storage_client: FileStorageClient,
        file_storage_scanner: FileStorageScanner,
        logger: ILogger,
        lock_manager: LockManager,
) -> ThumbnailService:
    """Provide thumbnail generation service."""
    return ThumbnailService(storage_client, file_storage_scanner, logger, lock_manager)


def _provide_healthcheck_service() -> AnyOf[HealthCheckReader, HealthCheckWriter]:
    """Provide health check service implementing reader and writer interfaces."""
    return HealthCheckService()


def _provide_lock_manager() -> LockManager:
    """Provide lock manager."""
    return LockManager()


def _provide_bucket_service(
        app_settings: AppSettings,
        storage_client: FileStorageClient,
) -> BucketService:
    """Provide bucket management service with bound logger."""
    logger = loguru.logger.bind(source="bucket_service")
    return MinioBucketService(
        app_settings=app_settings,
        storage_client=storage_client,
        l=logger,
    )


def _create_jwks(settings: OidcSettings) -> PyJWKClient:
    jwks_uri = settings.jwks_uri or urljoin(
        str(settings.issuer).rstrip("/") + "/",
        "protocol/openid-connect/certs"
    )

    return PyJWKClient(jwks_uri, cache_keys=True, lifespan=settings.jwks_ttl_seconds)


def _provide_jwt_verifier(
        auth: AuthSettings
) -> JWTVerifier:
    if auth.mode is AuthMode.off:
        return OffJWTVerifier()

    if not auth.oidc:
        raise ValueError("auth.oidc must be provided when auth.mode='oidc'")

    jwks = _create_jwks(auth.oidc)
    return OidcJWTVerifier(jwks, auth.oidc)


def _create_provider() -> Provider:
    """
    Create and configure the Dishka dependency injection provider.

    Groups providers by scope:
    - APP scope: long-lived dependencies (config, clients, services)
    - REQUEST scope: per-request dependencies (loggers, scanners)
    """
    provider = Provider()

    # Application-scoped providers
    provider.provide(_provide_app_settings, scope=Scope.APP)
    provider.provide(_provide_auth_settings, scope=Scope.APP)
    provider.provide(_provide_buckets_map, scope=Scope.APP)
    provider.provide(_provide_s3_settings, scope=Scope.APP)
    provider.provide(_provide_storage_client, scope=Scope.APP)
    provider.provide(_provide_healthcheck_service, scope=Scope.APP)
    provider.provide(_provide_minio_client, scope=Scope.APP)
    provider.provide(_provide_bucket_service, scope=Scope.APP)
    provider.provide(_provide_lock_manager, scope=Scope.APP)
    provider.provide(_provide_jwt_verifier, scope=Scope.APP)
    provider.provide(_provide_token_extractor, scope=Scope.APP)

    # Request-scoped providers
    provider.provide(_provide_request_logger, scope=Scope.REQUEST)
    provider.provide(_provide_file_storage_scanner, scope=Scope.REQUEST)
    provider.provide(_provide_thumbnail_service, scope=Scope.REQUEST)
    provider.provide(_provide_authenticator, scope=Scope.REQUEST)

    return provider


def _build_container() -> Container:
    """Build the dependency injection container with FastAPI integration."""
    provider = _create_provider()
    return make_container(provider, FastapiProvider())


container = _build_container()
