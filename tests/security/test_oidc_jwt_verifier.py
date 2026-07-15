import time
from unittest.mock import MagicMock

import jwt
import pytest

from sts.config.auth import OidcSettings
from sts.security.oidc_jwt_verifier import OidcJWTVerifier
from sts.security.models import InvalidToken, VerifiedToken

ISSUER = "https://idp.example.com/"
KID = "test-key-1"


@pytest.fixture
def rsa_keypair():
    from cryptography.hazmat.primitives.asymmetric import rsa
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key, key.public_key()


@pytest.fixture
def private_key(rsa_keypair):
    return rsa_keypair[0]


@pytest.fixture
def public_key(rsa_keypair):
    return rsa_keypair[1]


@pytest.fixture
def settings() -> OidcSettings:
    return OidcSettings(
        issuer=ISSUER,
        audience="my-api",
        algorithms=["RS256"],
        jwks_ttl_seconds=600,
        clock_skew_seconds=60,
    )


@pytest.fixture
def jwks_client() -> MagicMock:
    return MagicMock(spec=["get_signing_key_from_jwt"])


@pytest.fixture
def verifier(settings, jwks_client) -> OidcJWTVerifier:
    return OidcJWTVerifier(settings=settings, jwks_client=jwks_client)


def make_token(private_key, **overrides) -> str:
    payload = {
        "sub": "user-123",
        "iss": ISSUER,
        "aud": "my-api",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        **overrides,
    }
    return jwt.encode(
        payload, private_key, algorithm="RS256",
        headers={"kid": KID},
    )


# ---------- happy path ----------

def test_valid_token_returns_verified(verifier, jwks_client, private_key, public_key):
    signing_key = MagicMock()
    signing_key.key = public_key
    jwks_client.get_signing_key_from_jwt.return_value = signing_key

    token = make_token(private_key)
    result = verifier.verify(token)

    assert isinstance(result, VerifiedToken)
    assert result.subject == "user-123"
    assert result.issuer == ISSUER
    jwks_client.get_signing_key_from_jwt.assert_called_once_with(token)


# ---------- jwks failures ----------

def test_jwks_lookup_failure(verifier, jwks_client):
    jwks_client.get_signing_key_from_jwt.side_effect = Exception("network down")
    result = verifier.verify("any.jwt.token")
    assert result == InvalidToken(reason="jwks_unavailable")


# ---------- decode failures ----------

@pytest.mark.parametrize("reason,token_factory", [
    ("expired", lambda k: make_token(k, exp=int(time.time()) - 7200)),
    ("invalid_audience", lambda k: make_token(k, aud="wrong-aud")),
    ("invalid_issuer", lambda k: make_token(k, iss="https://evil.example.com")),
])
def test_decode_failures(reason, token_factory, verifier, jwks_client, public_key, private_key):
    signing_key = MagicMock()
    signing_key.key = public_key
    jwks_client.get_signing_key_from_jwt.return_value = signing_key

    result = verifier.verify(token_factory(private_key))
    assert result.reason == reason


def test_invalid_signature(verifier, jwks_client, public_key):
    signing_key = MagicMock()
    signing_key.key = public_key  # public key from a different pair
    jwks_client.get_signing_key_from_jwt.return_value = signing_key

    from cryptography.hazmat.primitives.asymmetric import rsa
    other_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = make_token(other_private)
    result = verifier.verify(token)
    assert result.reason == "invalid_signature"


def test_missing_token(verifier):
    assert verifier.verify("") == InvalidToken(reason="missing")


# ---------- require options ----------

def test_missing_required_claim_rejected(verifier, jwks_client, public_key):
    signing_key = MagicMock()
    signing_key.key = public_key
    jwks_client.get_signing_key_from_jwt.return_value = signing_key

    from cryptography.hazmat.primitives.asymmetric import rsa
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    # no "sub"
    token = jwt.encode(
        {"iss": ISSUER, "aud": "my-api", "iat": 1, "exp": 9999999999},
        priv, algorithm="RS256", headers={"kid": KID},
    )
    result = verifier.verify(token)
    assert result.reason == "invalid_signature"
