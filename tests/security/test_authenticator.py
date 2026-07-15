from unittest.mock import MagicMock

import pytest

from sts.config.auth import AuthMode
from sts.security.authenticator import Authenticator
from sts.security.models import (
    Anonymous, Authenticated, InvalidToken, VerifiedToken,
)


@pytest.fixture
def verifier() -> MagicMock:
    return MagicMock(spec=["verify"])


@pytest.fixture
def extractor() -> MagicMock:
    return MagicMock(spec=["extract"])


@pytest.fixture
def logger() -> MagicMock:
    return MagicMock(spec=["debug", "info", "warning", "error"])


@pytest.fixture
def authenticator(verifier, extractor, logger) -> Authenticator:
    return Authenticator(
        auth_mode=AuthMode.oidc,
        verifier=verifier,
        token_extractor=extractor,
        logger=logger,
    )


def test_is_required_true_for_oidc(authenticator):
    assert authenticator.is_required() is True


def test_is_required_false_for_off(verifier, extractor, logger):
    auth = Authenticator(AuthMode.off, verifier, extractor, logger)
    assert auth.is_required() is False


def test_no_token_returns_anonymous(verifier, authenticator, extractor):
    extractor.extract.return_value = None
    assert isinstance(authenticator.authenticate({}, {}), Anonymous)
    verifier.verify.assert_not_called()


def test_valid_token_returns_authenticated(authenticator, extractor, verifier):
    token = VerifiedToken(
        subject="user1", issuer="iss", audience="aud", expires_at=0, claims={}
    )
    extractor.extract.return_value = "raw.jwt.token"
    verifier.verify.return_value = token

    principal = authenticator.authenticate({}, {})
    assert isinstance(principal, Authenticated)
    assert principal.token is token
    verifier.verify.assert_called_once_with("raw.jwt.token")


def test_invalid_token_returns_anonymous(authenticator, extractor, verifier):
    extractor.extract.return_value = "bad.jwt.token"
    verifier.verify.return_value = InvalidToken(reason="expired")

    assert isinstance(authenticator.authenticate({}, {}), Anonymous)


@pytest.mark.parametrize("missing", ["verifier", "extractor", "logger"])
def test_missing_dependency_raises(missing, verifier, extractor, logger):
    deps = {"verifier": verifier, "extractor": extractor, "logger": logger, missing: None}
    with pytest.raises(ValueError):
        # pyrefly: ignore [bad-argument-type]
        Authenticator(AuthMode.oidc, deps["verifier"], deps["extractor"], deps["logger"])


def test_auth_mode_none_raises(verifier, extractor, logger):
    with pytest.raises(ValueError):
        # pyrefly: ignore [bad-argument-type]
        Authenticator(None, verifier, extractor, logger)


def test_passes_headers_and_cookies_to_extractor(authenticator, extractor, verifier):
    extractor.extract.return_value = None
    headers = {"Authorization": "Bearer x"}
    cookies = {"access_token": "y"}
    authenticator.authenticate(headers, cookies)
    extractor.extract.assert_called_once_with(headers=headers, cookies=cookies)
