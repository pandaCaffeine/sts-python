from dataclasses import dataclass
from typing import Mapping, Any


@dataclass(frozen=True, slots=True)
class VerifiedToken:
    subject: str
    issuer: str
    audience: str | list[str]
    expires_at: int
    claims: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class InvalidToken:
    reason: str


type VerificationResult = VerifiedToken | InvalidToken


@dataclass(frozen=True, slots=True)
class Anonymous:
    """ Marker for request tha did not present a valid token. """


@dataclass(frozen=True, slots=True)
class Authenticated:
    token: VerifiedToken


type Principal = Anonymous | Authenticated
