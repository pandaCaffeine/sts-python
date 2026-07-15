from pydantic import model_validator
import typing
from enum import StrEnum

from pydantic import BaseModel, HttpUrl


class AuthMode(StrEnum):
    off = "off"
    oidc = "oidc"


class OidcSettings(BaseModel):
    issuer: HttpUrl
    audience: str | list[str]
    jwks_uri: str | None = None
    jwks_ttl_seconds: int = 600
    algorithms: list[str] = ["RS256"]
    cookie_name: str = "access_token"
    clock_skew_seconds: int = 60


class AuthSettings(BaseModel):
    mode: AuthMode = AuthMode.off
    oidc: OidcSettings | None = None


    @model_validator(mode="after")
    def _require_oidc_when_enabled(self) -> typing.Self:
        if self.mode is AuthMode.oidc and not self.oidc:
            raise ValueError("auth.oidc must be provided when auth.mode='oidc'")
        return self
