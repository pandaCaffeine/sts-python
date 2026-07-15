from abc import abstractmethod
from typing import Protocol

from sts.security.models import VerificationResult


class JWTVerifier(Protocol):

    @abstractmethod
    def verify(self, token: str) -> VerificationResult:
        """ Validates JWT against an OIDC provider """
        ...
