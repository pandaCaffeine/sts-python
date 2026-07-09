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


