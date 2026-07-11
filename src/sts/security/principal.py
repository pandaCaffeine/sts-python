from dataclasses import dataclass
from sts.security.models import VerifiedToken


@dataclass(frozen=True, slots=True)
class Anonymous:
    """ Marker for request tha did not present a valid token. """


@dataclass(frozen=True, slots=True)
class Authenticated:
    token: VerifiedToken


Principal = Anonymous | Authenticated
