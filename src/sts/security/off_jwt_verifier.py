from typing import override

from sts.security.jwt_verifier import JWTVerifier
from sts.security.models import VerifiedToken, InvalidToken


class OffJWTVerifier(JWTVerifier):

    @override
    def verify(self, token: str) -> VerifiedToken | InvalidToken:
       return InvalidToken(reason="auth_disabled")
