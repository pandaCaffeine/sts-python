import pytest

from sts.security.models import InvalidToken
from sts.security.off_jwt_verifier import OffJWTVerifier


@pytest.fixture
def off_jwt_verifier() -> OffJWTVerifier:
    return OffJWTVerifier()

@pytest.mark.parametrize("token", ["", "AFSFSA123", "DSAW", None, "123", "--="])
def test_off_jwt_verifier_returns_invalid_token(off_jwt_verifier: OffJWTVerifier, token: str):
    result = off_jwt_verifier.verify(token)
    assert isinstance(result, InvalidToken)
    assert result.reason == "auth_disabled"