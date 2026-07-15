import fastapi
from dishka import FromDishka
from dishka.integrations.fastapi import inject_sync

from sts.security.authenticator import Authenticator
from sts.security.models import Principal, Anonymous


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
