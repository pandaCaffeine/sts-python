from typing import Mapping

from sts.config.auth import AuthMode
from sts.logs import ILogger
from sts.security.extractor import TokenExtractor
from sts.security.jwt_verifier import JWTVerifier
from sts.security.models import InvalidToken
from sts.security.models import Principal, Anonymous, Authenticated


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
