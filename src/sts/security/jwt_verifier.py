from abc import abstractmethod
from typing import Protocol

from sts.security.models import VerifiedToken, InvalidToken


class JWTVerifier(Protocol):

    @abstractmethod
    def verify(self, token: str) -> VerifiedToken | InvalidToken:
        """ Validates JWT against an OIDC provider """
        ...
