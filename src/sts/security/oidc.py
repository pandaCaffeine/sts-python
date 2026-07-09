from urllib.parse import urljoin

from jwt import PyJWKClient, ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError, InvalidSignatureError, \
    InvalidTokenError, decode

from sts.config.auth import OidcSettings
from sts.logs import ILogger
from sts.security.jwt_verifier import JWTVerifier
from sts.security.models import VerifiedToken, InvalidToken


class OidcJWTVerifier(JWTVerifier):

    def __init__(self, settings: OidcSettings, logger: ILogger) -> None:
        if not settings:
            raise ValueError("settings is required")
        if not logger:
            raise ValueError("logger is required")

        self._settings = settings
        self._logger = logger

        jwks_uri = settings.jwks_uri or urljoin(
            str(settings.issuer).rstrip("/") + "/",
            "protocol/openid-connect/certs"
        )

        self._jwks_client = PyJWKClient(
            jwks_uri,
            cache_keys=True,
            lifespan=settings.jwks_ttl_seconds
        )

    def verify(self, token: str) -> VerifiedToken | InvalidToken:
        if not token:
            return InvalidToken(reason="missing")

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        except Exception as exc:
            self._logger.debug(f"JWKS lookup failed: {exc}")
            return InvalidToken(reason="jwks_unavailable")

        try:
            claims = decode(
                token,
                signing_key.key,
                algorithms=self._settings.algorithms,
                audience=self._settings.audience,
                issuer=str(self._settings.issuer),
                leeway=self._settings.clock_skew_seconds,
                options={"require": ["exp", "iat", "iss", "sub"]}
            )
        except ExpiredSignatureError:
            return InvalidToken(reason="expired")
        except InvalidAudienceError:
            return InvalidToken(reason="invalid_audience")
        except InvalidIssuerError:
            return InvalidToken(reason="invalid_issuer")
        except InvalidSignatureError:
            return InvalidToken(reason="invalid_signature")
        except InvalidTokenError as exc:  # все остальные JWT-ошибки
            return InvalidToken(reason=f"invalid:{type(exc).__name__}")
        except Exception as exc:  # неизвестное — fail-closed
            self._logger.warning(f"Unexpected JWT decode error: {exc}")
            return InvalidToken(reason="invalid")

        return VerifiedToken(
            subject=str(claims.get("sub", "")),
            issuer=str(claims.get("iss", "")),
            audience=claims.get("aud", ""),
            expires_at=int(claims.get("exp", 0)),
            claims=claims
        )
