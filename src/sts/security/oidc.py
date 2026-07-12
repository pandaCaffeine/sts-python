from typing import override
from urllib.parse import urljoin

import loguru
from jwt import PyJWKClient, ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError, InvalidSignatureError, \
    InvalidTokenError, decode

from sts.config.auth import OidcSettings
from sts.security.jwt_verifier import JWTVerifier
from sts.security.models import VerifiedToken, InvalidToken


class OidcJWTVerifier(JWTVerifier):

    def __init__(self, settings: OidcSettings) -> None:
        if settings is None:
            raise ValueError("settings is required")

        self._settings = settings
        self._logger = loguru.logger.bind(source="oidc_jwt_verifier")

        jwks_uri = settings.jwks_uri or urljoin(
            str(settings.issuer).rstrip("/") + "/",
            "protocol/openid-connect/certs"
        )

        self._jwks_client = PyJWKClient(
            jwks_uri,
            cache_keys=True,
            lifespan=settings.jwks_ttl_seconds
        )

    @override
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
        except InvalidTokenError as exc:  # any other JWT error
            return InvalidToken(reason=f"invalid:{type(exc).__name__}")
        except Exception as exc:  # unknown error
            self._logger.warning(f"Unexpected JWT decode error: {exc}")
            return InvalidToken(reason="invalid")

        return VerifiedToken(
            subject=str(claims.get("sub", "")),
            issuer=str(claims.get("iss", "")),
            audience=claims.get("aud", ""),
            expires_at=int(claims.get("exp", 0)),
            claims=claims
        )
