from dishka import FromDishka
from typing import Annotated

from fastapi import Response
import math

from fastapi.params import Depends

from sts.security.principal import Principal, Anonymous, Authenticated
from fastapi import Request
from sts.config.auth import AuthSettings
from sts.logs import ILogger
from sts.security.extractor import TokenExtractor
from sts.security.jwt_verifier import JWTVerifier


def make_token_extractor(auth: AuthSettings) -> TokenExtractor:
    """ Builds a :class:`TokenExtractor` for the active auth mode.

    For ``mode=off`` still creates one with a default cookie name.
    """

    cookie_name = auth.oidc.cookie_name if auth.oidc else "access_token"
    return TokenExtractor(cookie_name=cookie_name)


def _build_principal(
        request: Request,
        extractor: TokenExtractor,
        verifier: JWTVerifier,
        logger: ILogger,
) -> Principal:
    token = extractor.extract(request.headers, request.cookies)
    if not token:
        logger.debug("No bearer token found in request")
        return Anonymous()

    result = verifier.verify(token)
    match result:
        case None:
            return Anonymous()
        case Anonymous():
            return result
        case _:
            pass

    from sts.security.models import InvalidToken

    if isinstance(result, InvalidToken):
        logger.debug(f"Token rejected: {result.reason}")
        return Anonymous()
    return Authenticated(token=result)


def current_principal(
        request: Request,
        extractor: Annotated[TokenExtractor, Depends(make_token_extractor)],
        verifier: FromDishka[JWTVerifier],
        logger: FromDishka[ILogger]
) -> Principal:
    """FastAPI dependency returning the request's :class:`Principal`."""
    return _build_principal(request, extractor, verifier, logger)


def require_auth(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
    """FastAPI dependency enforcing that the request is authenticated."""

    if isinstance(principal, Anonymous):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal
