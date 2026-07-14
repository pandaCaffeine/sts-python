from typing import Mapping

import fastapi
from dishka import FromDishka
from dishka.integrations.fastapi import inject_sync

from sts.config.auth import AuthMode
from sts.logs import ILogger
from sts.security.extractor import TokenExtractor
from sts.security.jwt_verifier import JWTVerifier
from sts.security.models import InvalidToken
from sts.security.principal import Principal, Anonymous, Authenticated


class Authenticator:
    def __init__(self, auth_mode: AuthMode, verifier: JWTVerifier,
                 token_extractor: TokenExtractor,
                 logger: ILogger) -> None:
        if verifier is None:
            raise ValueError("verifier is required")
        if auth_mode is None:
            raise ValueError("auth_mode is required")
        if token_extractor is None:
            raise ValueError("token_extractor is required")
        if logger is None:
            raise ValueError("logger is required")

        self._verifier = verifier
        self._auth_mode = auth_mode
        self._logger = logger
        self._extractor = token_extractor

    def is_required(self) -> bool:
        """ Returns TRUE is authentication is required according to auth configs. """
        return self._auth_mode is AuthMode.oidc

    def authenticate(
            self,
            headers: Mapping[str, str],
            cookies: Mapping[str, str]
    ) -> Principal:
        token = self._extractor.extract(headers=headers, cookies=cookies)
        if not token:
            self._logger.debug("No bearer token found in request")
            return Anonymous()

        result = self._verifier.verify(token)
        if isinstance(result, InvalidToken):
            self._logger.debug(f"Token rejected: {result.reason}")
            return Anonymous()

        return Authenticated(token=result)


@inject_sync
def require_auth(
        request: fastapi.Request,
        authenticator: FromDishka[Authenticator]) -> Principal:
    """FastAPI dependency enforcing that the request is authenticated."""

    if not authenticator.is_required():
        return Anonymous()

    principal = authenticator.authenticate(
        headers=request.headers,
        cookies=request.cookies
    )

    if isinstance(principal, Anonymous):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={'status': status.HTTP_401_UNAUTHORIZED, 'message': 'Authentication required'},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return principal
