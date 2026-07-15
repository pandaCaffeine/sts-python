from functools import lru_cache

from sts.config.auth import AuthSettings
from sts.config.models import AppSettings


@lru_cache
def get_app_settings() -> AppSettings:
    """Get the cached application settings instance.

    Returns:
        The singleton AppSettings instance.
    """
    return AppSettings()

@lru_cache()
def get_auth_settings() -> AuthSettings:
    """ Returns cached auth settings instance.

    Returns:
        The singleton AuthSettings instance.
    """
    return get_app_settings().auth
