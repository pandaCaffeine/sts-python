from typing import override

from sts.security.jwt_verifier import JWTVerifier
from sts.security.models import InvalidToken, VerificationResult


class OffJWTVerifier(JWTVerifier):

    @override
    def verify(self, token: str) -> VerificationResult:
        return InvalidToken(reason="auth_disabled")
