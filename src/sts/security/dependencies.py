from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Request
from fastapi.params import Depends

from sts.config.auth import AuthSettings, AuthMode
from sts.logs import ILogger
from sts.security.extractor import TokenExtractor
from sts.security.jwt_verifier import JWTVerifier
from sts.security.models import InvalidToken
from sts.security.principal import Principal, Anonymous, Authenticated


def _build_principal(
        request: Request,
        auth: AuthSettings,
        verifier: JWTVerifier,
        logger: ILogger,
) -> Principal:
    if auth.mode is AuthMode.off:
        logger.debug("auth is disabled, request treated as anonymous")
        return Anonymous()

    cookie_name = auth.oidc.cookie_name if auth.oidc else "access_token"
    extractor = TokenExtractor(cookie_name=cookie_name)
    token = extractor.extract(request.headers, request.cookies)
    if not token:
        logger.debug("No bearer token found in request")
        return Anonymous()

    result = verifier.verify(token)
    if isinstance(result, InvalidToken):
        logger.debug(f"Token rejected: {result.reason}")
        return Anonymous()

    return Authenticated(token=result)


@inject
def current_principal(
        request: Request,
        auth: FromDishka[AuthSettings],
        verifier: FromDishka[JWTVerifier],
        logger: FromDishka[ILogger]
) -> Principal:
    """FastAPI dependency returning the request's :class:`Principal`."""
    return _build_principal(request, auth, verifier, logger)


@inject
def require_auth(principal: Annotated[Principal, Depends(current_principal)],
                 auth: FromDishka[AuthSettings]) -> Principal:
    """FastAPI dependency enforcing that the request is authenticated."""

    if auth.mode is AuthMode.off:
        return principal

    if isinstance(principal, Anonymous):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal
